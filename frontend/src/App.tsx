import { useMemo, useState } from "react";
import { createSearch, reviewResults, reviewSpec } from "./api";
import type {
  CandidateProfile,
  CandidateScore,
  FeedbackDecision,
  FeedbackItem,
  FitRubric,
  InterruptPayload,
  ObjectiveFilters,
  SearchState,
  WorkflowResponse,
} from "./types";

const exampleQuery =
  "Backend developers with 1-4 years of experience who have worked at startups, based in Bangalore, with PostgreSQL experience.";

const emptyFilters: ObjectiveFilters = {
  required_skills: [],
  preferred_skills: [],
  min_years_experience: null,
  max_years_experience: null,
  locations: [],
  company_types: [],
  past_company_keywords: [],
};

const emptyRubric: FitRubric = {
  criteria: [
    {
      name: "Relevant experience",
      description: "Evidence that the candidate has done comparable work.",
      weight: 1,
    },
  ],
};

function App() {
  const [query, setQuery] = useState("");
  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const [filters, setFilters] = useState<ObjectiveFilters>(emptyFilters);
  const [rubric, setRubric] = useState<FitRubric>(emptyRubric);
  const [feedback, setFeedback] = useState<Record<string, FeedbackItem>>({});
  const [overallFeedback, setOverallFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeNav, setActiveNav] = useState("Search");

  const state = workflow?.state ?? null;
  const interrupt = workflow?.interrupt ?? null;
  const stage = interrupt?.type ?? (state?.frozen ? "frozen" : "idle");
  const isResultsStage = stage === "review_results";
  const isSpecStage = stage === "review_spec";
  const isFrozen = stage === "frozen" || Boolean(state?.frozen);

  const candidateMap = useMemo(
    () => new Map((state?.candidate_profiles ?? []).map((candidate) => [candidate.id, candidate])),
    [state?.candidate_profiles],
  );

  function applyWorkflowResponse(response: WorkflowResponse) {
    setWorkflow(response);
    setError(null);
    if (response.interrupt?.type === "review_spec") {
      setFilters(response.interrupt.filters ?? response.state.filters ?? emptyFilters);
      setRubric(response.interrupt.rubric ?? response.state.rubric ?? emptyRubric);
    }
  }

  async function runAction(action: () => Promise<WorkflowResponse>) {
    setBusy(true);
    setError(null);
    try {
      applyWorkflowResponse(await action());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  function startSearch() {
    if (query.trim().length < 3) {
      setError("Describe the role in a little more detail first.");
      return;
    }
    setFeedback({});
    setOverallFeedback("");
    void runAction(() => createSearch(query.trim()));
  }

  function approveSpec() {
    if (!state) return;
    void runAction(() => reviewSpec(state.search_id, filters, rubric));
  }

  function submitResults(action: "refine" | "freeze") {
    if (!state) return;
    const selectedFeedback = Object.values(feedback).filter((item) => item.decision !== "maybe" || item.comment);
    void runAction(() => reviewResults(state.search_id, action, selectedFeedback, overallFeedback));
  }

  return (
    <div className="app-shell">
      <Sidebar activeNav={activeNav} onNavigate={setActiveNav} />
      <main className="main-content">
        <Topbar state={state} stage={stage} />

        {activeNav !== "Search" ? (
          <PlaceholderPanel title={activeNav} />
        ) : (
          <>
            <section className="welcome-row">
              <div>
                <p className="eyebrow">RECRUITING INTELLIGENCE / WORKSPACE</p>
                <h1>Find people who fit the work.</h1>
                <p className="welcome-copy">
                  Turn a hiring instinct into a transparent, editable shortlist your team can trust.
                </p>
              </div>
              <div className="round-stat">
                <span className="stat-label">REFINEMENT ROUND</span>
                <strong>{state?.refinement_round ?? 0}</strong>
                <span className="stat-caption">of this search</span>
              </div>
            </section>

            <StageRail stage={stage} />

            <section className="workspace-grid">
              <div className="workspace-primary">
                <SearchComposer
                  query={query}
                  setQuery={setQuery}
                  onUseExample={() => setQuery(exampleQuery)}
                  onSubmit={startSearch}
                  busy={busy}
                  hasSearch={Boolean(state)}
                />

                {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

                {isSpecStage && (
                  <SpecReview
                    filters={filters}
                    rubric={rubric}
                    setFilters={setFilters}
                    setRubric={setRubric}
                    onApprove={approveSpec}
                    busy={busy}
                    diagnostics={state?.diagnostics ?? null}
                    changes={interrupt?.changes ?? state?.changes ?? []}
                  />
                )}

                {isResultsStage && state && (
                  <ResultsReview
                    state={state}
                    candidateMap={candidateMap}
                    feedback={feedback}
                    setFeedback={setFeedback}
                    overallFeedback={overallFeedback}
                    setOverallFeedback={setOverallFeedback}
                    onRefine={() => submitResults("refine")}
                    onFreeze={() => submitResults("freeze")}
                    busy={busy}
                  />
                )}

                {isFrozen && state && <FrozenSummary state={state} candidateMap={candidateMap} />}

                {!state && !busy && <EmptyWelcome onUseExample={() => setQuery(exampleQuery)} />}
                {busy && <LoadingPanel stage={stage} />}
              </div>

              <aside className="workspace-aside">
                <SearchContext state={state} stage={stage} />
                <ActivityPanel state={state} />
              </aside>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function Sidebar({ activeNav, onNavigate }: { activeNav: string; onNavigate: (value: string) => void }) {
  return (
    <aside className="sidebar">
      <div className="brand-lockup">
        <div className="brand-mark">S</div>
        <div>
          <strong>scoutwise</strong>
          <span>recruiting intelligence</span>
        </div>
      </div>
      <div className="sidebar-label">WORKSPACE</div>
      <nav>
        {[
          ["⌕", "Search"],
          ["◫", "Shortlists"],
          ["◌", "Playbook"],
        ].map(([icon, label]) => (
          <button className={`nav-item ${activeNav === label ? "active" : ""}`} key={label} onClick={() => onNavigate(label)}>
            <span className="nav-icon">{icon}</span>{label}
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-label">YOUR SIGNAL</div>
        <div className="signal-card"><span className="signal-dot" />AI model online<span className="signal-ping" /></div>
        <div className="profile-chip"><div className="avatar avatar-small">PK</div><span>Recruiter workspace</span><span className="chevron">⌄</span></div>
      </div>
    </aside>
  );
}

function Topbar({ state, stage }: { state: SearchState | null; stage: string }) {
  return (
    <header className="topbar">
      <div className="breadcrumb"><span>Workspace</span><b>/</b><strong>{state ? "Active search" : "New search"}</strong></div>
      <div className="topbar-actions">
        <span className="connection"><span className="connection-dot" /> API connected</span>
        <button className="icon-button" aria-label="Notifications">♧<span className="notification-dot" /></button>
        <div className="avatar">PK</div>
      </div>
    </header>
  );
}

function StageRail({ stage }: { stage: string }) {
  const stages = [
    ["search", "Search"],
    ["review_spec", "Shape the brief"],
    ["review_results", "Review people"],
    ["frozen", "Freeze shortlist"],
  ];
  const currentIndex = stage === "idle" ? 0 : stage === "review_spec" ? 1 : stage === "review_results" ? 2 : 3;
  return <div className="stage-rail">{stages.map(([key, label], index) => <div className={`stage-step ${index <= currentIndex ? "complete" : ""} ${key === stage ? "current" : ""}`} key={key}><span className="stage-number">{index < currentIndex ? "✓" : index + 1}</span><span>{label}</span>{index < stages.length - 1 && <i />}</div>)}</div>;
}

function SearchComposer({ query, setQuery, onUseExample, onSubmit, busy, hasSearch }: { query: string; setQuery: (value: string) => void; onUseExample: () => void; onSubmit: () => void; busy: boolean; hasSearch: boolean }) {
  return <section className="search-composer panel">
    <div className="panel-heading"><div><span className="section-kicker">START WITH INTENT</span><h2>What are you looking for?</h2></div><span className="shortcut">⌘ K</span></div>
    <div className="search-input-wrap"><span className="search-icon">⌕</span><textarea value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Describe the role, the context, and what great looks like..." rows={2} /><button className="clear-button" onClick={() => setQuery("")} aria-label="Clear search">×</button></div>
    <div className="composer-footer"><div className="example-prompt"><span>Try:</span><button onClick={onUseExample}>“Backend developers with startup experience in Bangalore”</button></div><button className="primary-button" disabled={busy} onClick={onSubmit}>{busy ? "Thinking..." : hasSearch ? "Run new search" : "Shape the search"}<span>→</span></button></div>
  </section>;
}

function SpecReview({ filters, rubric, setFilters, setRubric, onApprove, busy, diagnostics, changes }: { filters: ObjectiveFilters; rubric: FitRubric; setFilters: (value: ObjectiveFilters) => void; setRubric: (value: FitRubric) => void; onApprove: () => void; busy: boolean; diagnostics: SearchState["diagnostics"]; changes: string[] }) {
  return <section className="panel spec-panel">
    <div className="panel-heading"><div><span className="section-kicker">HUMAN REVIEW / 01</span><h2>Shape the search</h2><p className="panel-subtitle">The AI translated your brief. Edit the signal before we look at people.</p></div><span className="ai-badge">✦ AI draft</span></div>
    {diagnostics && diagnostics.matched_candidates === 0 && <div className="warning-banner"><span>!</span><div><strong>No profiles matched these filters.</strong><p>Loosen a constraint and we’ll run the search again.</p></div></div>}
    {changes.length > 0 && <div className="assumption-note"><span>✦</span><div><strong>AI notes for your review</strong><p>{changes.join(" · ")}</p></div></div>}
    <div className="spec-grid"><FilterEditor filters={filters} setFilters={setFilters} /><RubricEditor rubric={rubric} setRubric={setRubric} /></div>
    <div className="panel-footer align-end"><span className="helper-copy">You stay in control. Nothing runs until you approve the brief.</span><button className="primary-button" onClick={onApprove} disabled={busy}>Run against talent map <span>→</span></button></div>
  </section>;
}

function FilterEditor({ filters, setFilters }: { filters: ObjectiveFilters; setFilters: (value: ObjectiveFilters) => void }) {
  const [skillInput, setSkillInput] = useState("");
  const [locationInput, setLocationInput] = useState("");
  const addValue = (key: "required_skills" | "preferred_skills" | "locations" | "past_company_keywords", value: string) => { if (!value.trim()) return; const values = filters[key].includes(value.trim()) ? filters[key] : [...filters[key], value.trim()]; setFilters({ ...filters, [key]: values }); };
  const removeValue = (key: "required_skills" | "preferred_skills" | "locations" | "past_company_keywords", value: string) => setFilters({ ...filters, [key]: filters[key].filter((item) => item !== value) });
  return <div className="editor-column"><div className="editor-heading"><span className="editor-icon blue">⌁</span><div><h3>Objective filters</h3><p>Must be true in the profile data.</p></div></div>
    <label>Required skills <span className="label-hint">hard signal</span></label><div className="chip-input"><ChipList values={filters.required_skills} onRemove={(value) => removeValue("required_skills", value)} /><input value={skillInput} onChange={(event) => setSkillInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { addValue("required_skills", skillInput); setSkillInput(""); } }} placeholder="Add skill + Enter" /></div>
    <label>Preferred skills <span className="label-hint soft">soft signal</span></label><div className="chip-input"><ChipList values={filters.preferred_skills} onRemove={(value) => removeValue("preferred_skills", value)} /><input value={filters.preferred_skills.join(", ")} onChange={(event) => setFilters({ ...filters, preferred_skills: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} placeholder="e.g. Redis, AWS" /></div>
    <div className="two-fields"><div><label>Experience <span className="label-hint">years</span></label><div className="range-input"><input type="number" min="0" value={filters.min_years_experience ?? ""} onChange={(event) => setFilters({ ...filters, min_years_experience: event.target.value ? Number(event.target.value) : null })} placeholder="Min" /><span>to</span><input type="number" min="0" value={filters.max_years_experience ?? ""} onChange={(event) => setFilters({ ...filters, max_years_experience: event.target.value ? Number(event.target.value) : null })} placeholder="Max" /></div></div><div><label>Locations</label><div className="chip-input compact"><ChipList values={filters.locations} onRemove={(value) => removeValue("locations", value)} /><input value={locationInput} onChange={(event) => setLocationInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { addValue("locations", locationInput); setLocationInput(""); } }} placeholder="Add location" /></div></div></div>
    <label>Company context</label><div className="check-row">{["startup", "scaleup", "enterprise", "agency"].map((type) => <label className="check-label" key={type}><input type="checkbox" checked={filters.company_types.includes(type)} onChange={(event) => setFilters({ ...filters, company_types: event.target.checked ? [...filters.company_types, type] : filters.company_types.filter((item) => item !== type) })} /><span>{type}</span></label>)}</div>
  </div>;
}

function RubricEditor({ rubric, setRubric }: { rubric: FitRubric; setRubric: (value: FitRubric) => void }) {
  function update(index: number, patch: Partial<FitRubric["criteria"][number]>) { setRubric({ criteria: rubric.criteria.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) }); }
  return <div className="editor-column rubric-column"><div className="editor-heading"><span className="editor-icon coral">✦</span><div><h3>Fit rubric</h3><p>How we’ll compare the people who pass.</p></div></div><div className="rubric-list">{rubric.criteria.map((criterion, index) => <div className="rubric-item" key={`${criterion.name}-${index}`}><div className="rubric-item-top"><input className="criterion-name" value={criterion.name} onChange={(event) => update(index, { name: event.target.value })} /><span className="weight-pill">{Math.round(criterion.weight * 100)}%</span></div><textarea value={criterion.description} onChange={(event) => update(index, { description: event.target.value })} rows={2} /><input type="range" min="0.05" max="1" step="0.05" value={criterion.weight} onChange={(event) => update(index, { weight: Number(event.target.value) })} /></div>)}</div><button className="text-button" onClick={() => setRubric({ criteria: [...rubric.criteria, { name: "New criterion", description: "What evidence should we look for?", weight: 0.2 }] })}>＋ Add criterion</button></div>;
}

function ChipList({ values, onRemove }: { values: string[]; onRemove: (value: string) => void }) { return <>{values.map((value) => <span className="chip" key={value}>{value}<button onClick={() => onRemove(value)}>×</button></span>)}</>; }

function ResultsReview({ state, candidateMap, feedback, setFeedback, overallFeedback, setOverallFeedback, onRefine, onFreeze, busy }: { state: SearchState; candidateMap: Map<string, CandidateProfile>; feedback: Record<string, FeedbackItem>; setFeedback: (value: Record<string, FeedbackItem>) => void; overallFeedback: string; setOverallFeedback: (value: string) => void; onRefine: () => void; onFreeze: () => void; busy: boolean }) {
  const updateFeedback = (candidateId: string, decision: FeedbackDecision) => setFeedback({ ...feedback, [candidateId]: { candidate_id: candidateId, decision, comment: feedback[candidateId]?.comment ?? "" } });
  return <section className="results-section"><div className="results-header"><div><span className="section-kicker">HUMAN REVIEW / 02</span><h2>Your first signal set</h2><p className="panel-subtitle">{state.results.length} profiles ranked from {state.diagnostics?.total_candidates ?? "the"} in the talent map.</p></div><div className="results-header-actions"><button className="secondary-button">↕ Sort: best fit</button><button className="secondary-button">☷ View options</button></div></div><div className="results-layout"><div className="candidate-list">{state.results.map((result, index) => <CandidateCard key={result.candidate_id} rank={index + 1} score={result} profile={candidateMap.get(result.candidate_id)} feedback={feedback[result.candidate_id]} onDecision={(decision) => updateFeedback(result.candidate_id, decision)} onComment={(comment) => setFeedback({ ...feedback, [result.candidate_id]: { candidate_id: result.candidate_id, decision: feedback[result.candidate_id]?.decision ?? "maybe", comment } })} />)}</div><div className="feedback-panel panel"><div className="panel-heading compact-heading"><div><span className="section-kicker">YOUR SIGNAL</span><h3>Shape the next round</h3></div><span className="feedback-count">{Object.keys(feedback).length}</span></div><p className="panel-subtitle">Tell the AI what to tune. Your feedback changes the next filters and rubric.</p><textarea value={overallFeedback} onChange={(event) => setOverallFeedback(event.target.value)} placeholder="e.g. Show me only people based in Bangalore, and prioritize startup ownership over years of experience..." rows={6} /><div className="feedback-summary"><span className="tiny-dot green" />{Object.values(feedback).filter((item) => item.decision === "accept").length} strong matches <span className="tiny-dot red" />{Object.values(feedback).filter((item) => item.decision === "reject").length} to reconsider</div><button className="primary-button full-button" disabled={busy} onClick={onRefine}>Refine with this signal <span>→</span></button><button className="freeze-button" disabled={busy} onClick={onFreeze}>♢ Freeze this shortlist</button></div></div></section>;
}

function CandidateCard({ rank, score, profile, feedback, onDecision, onComment }: { rank: number; score: CandidateScore; profile?: CandidateProfile; feedback?: FeedbackItem; onDecision: (decision: FeedbackDecision) => void; onComment: (comment: string) => void }) {
  const initials = profile?.name.split(" ").map((part) => part[0]).join("").slice(0, 2) ?? "?";
  return <article className={`candidate-card ${feedback?.decision === "reject" ? "dimmed-card" : ""}`}><div className="candidate-top"><span className="rank">0{rank}</span><div className="avatar candidate-avatar">{initials}</div><div className="candidate-identity"><h3>{profile?.name ?? score.candidate_id}</h3><p>{profile?.current_title ?? "Candidate profile"} <span>·</span> {profile?.location ?? "Location unknown"}</p></div><div className="score-ring"><strong>{Math.round(score.score)}</strong><span>fit</span></div></div><div className="candidate-meta"><span>◷ {profile?.years_experience ?? "—"} yrs exp</span><span>◈ {profile?.current_company ?? "—"}</span><span className="company-tag">{profile?.current_company_type ?? "profile"}</span></div><p className="candidate-summary">{score.explanation}</p><div className="evidence-row">{score.evidence.slice(0, 3).map((item) => <span key={item}>✓ {item}</span>)}</div><div className="strength-concern"><div><span className="mini-heading positive">STRENGTHS</span>{score.strengths.slice(0, 2).map((item) => <p key={item}>+ {item}</p>)}</div><div><span className="mini-heading caution">WATCH FOR</span>{score.concerns.slice(0, 2).map((item) => <p key={item}>! {item}</p>)}</div></div><div className="card-footer"><div className="feedback-buttons"><span className="feedback-label">Is this useful?</span><button className={feedback?.decision === "accept" ? "selected-yes" : ""} onClick={() => onDecision("accept")}>✓ Good match</button><button className={feedback?.decision === "reject" ? "selected-no" : ""} onClick={() => onDecision("reject")}>× Not for me</button><button className={feedback?.decision === "maybe" ? "selected-maybe" : ""} onClick={() => onDecision("maybe")}>◌ Maybe</button></div>{feedback && <input className="inline-comment" value={feedback.comment} onChange={(event) => onComment(event.target.value)} placeholder="Add a note..." />}</div></article>;
}

function FrozenSummary({ state, candidateMap }: { state: SearchState; candidateMap: Map<string, CandidateProfile> }) { return <section className="panel frozen-panel"><div className="frozen-banner"><span>✓</span><div><span className="section-kicker">SEARCH FROZEN</span><h2>Your shortlist is ready</h2><p>The final state is locked after {state.refinement_round} refinement round{state.refinement_round === 1 ? "" : "s"}.</p></div></div><div className="frozen-grid"><div><span className="section-kicker">FINAL FILTERS</span><FilterSummary filters={state.filters} /></div><div><span className="section-kicker">FINAL RUBRIC</span><div className="final-rubric">{state.rubric?.criteria.map((criterion) => <div key={criterion.name}><strong>{criterion.name}</strong><span>{Math.round(criterion.weight * 100)}%</span></div>)}</div></div></div><div className="shortlist-row"><span className="section-kicker">TOP MATCHES</span><div className="frozen-candidates">{state.results.slice(0, 5).map((result) => <div className="frozen-candidate" key={result.candidate_id}><div className="avatar avatar-small">{candidateMap.get(result.candidate_id)?.name.slice(0, 2).toUpperCase() ?? "?"}</div><div><strong>{candidateMap.get(result.candidate_id)?.name ?? result.candidate_id}</strong><span>{Math.round(result.score)} fit score</span></div></div>)}</div></div></section>; }

function FilterSummary({ filters }: { filters: ObjectiveFilters | null }) { if (!filters) return <p className="muted">No filters yet.</p>; const values = [...filters.required_skills, ...filters.locations, ...filters.company_types]; return <div className="summary-chips">{values.map((value) => <span className="chip muted-chip" key={value}>{value}</span>)}{filters.min_years_experience !== null && <span className="chip muted-chip">{filters.min_years_experience}-{filters.max_years_experience ?? "∞"} years</span>}</div>; }

function SearchContext({ state, stage }: { state: SearchState | null; stage: string }) { return <div className="context-card panel"><div className="context-top"><span className="section-kicker">SEARCH CONTEXT</span><span className={`live-pill ${stage === "frozen" ? "frozen-pill" : ""}`}><span />{stage === "frozen" ? "Frozen" : state ? "Live" : "Ready"}</span></div><p className="context-query">{state?.original_query ?? "Your next great hire starts with a clear signal."}</p>{state && <><div className="context-divider" /><div className="context-stat"><span>Profiles considered</span><strong>{state.diagnostics?.total_candidates ?? "—"}</strong></div><div className="context-stat"><span>Current shortlist</span><strong>{state.results.length || state.diagnostics?.matched_candidates || "—"}</strong></div></>}</div>; }

function ActivityPanel({ state }: { state: SearchState | null }) { return <div className="activity-card panel"><div className="panel-heading compact-heading"><div><span className="section-kicker">WORKFLOW</span><h3>Search pulse</h3></div><span className="pulse-icon">◌</span></div><div className="activity-list"><ActivityItem done={Boolean(state)} title="Search brief captured" detail={state ? "Natural language understood" : "Waiting for your brief"} /><ActivityItem done={Boolean(state?.filters)} title="Signal shaped" detail={state?.filters ? "Filters ready for review" : "AI will extract the signal"} /><ActivityItem done={Boolean(state?.results.length)} title="People ranked" detail={state?.results.length ? `${state.results.length} profiles surfaced` : "Runs after approval"} /><ActivityItem done={Boolean(state?.frozen)} title="Shortlist frozen" detail={state?.frozen ? "Ready to share" : "Your decision"} last /></div></div>; }

function ActivityItem({ done, title, detail, last }: { done: boolean; title: string; detail: string; last?: boolean }) { return <div className={`activity-item ${done ? "done" : ""}`}><span className="activity-marker">{done ? "✓" : "·"}</span>{!last && <i /> }<div><strong>{title}</strong><span>{detail}</span></div></div>; }

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) { return <div className="error-banner"><span className="error-symbol">!</span><div><strong>Oops there is some system issue. Sorry for the inconvenience. Please try later</strong><p>{message}</p></div><button onClick={onDismiss}>×</button></div>; }
function LoadingPanel({ stage }: { stage: string }) { return <div className="loading-panel panel"><span className="loader" /><div><strong>{stage === "review_spec" ? "Reading the brief..." : "Working through the talent map..."}</strong><span>The AI is keeping the reasoning grounded in your search.</span></div></div>; }
function EmptyWelcome({ onUseExample }: { onUseExample: () => void }) { return <div className="empty-welcome"><div className="empty-orbit">✦</div><h2>A more thoughtful way to search.</h2><p>Start with the kind of person you want to meet. Scoutwise will turn your instinct into a visible, editable search.</p><button className="secondary-button" onClick={onUseExample}>Use an example brief <span>→</span></button></div>; }
function PlaceholderPanel({ title }: { title: string }) { return <div className="placeholder-panel panel"><span className="empty-orbit">✦</span><h2>{title} is coming next.</h2><p>The focused recruiter workspace is ready for the search loop. This area will grow with your workflow.</p></div>; }

export default App;
