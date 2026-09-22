# Backend Implementation Guide

## Purpose

The backend implements the recruiter-facing sourcing refinement loop from the Flexiple hiring challenge. It accepts a natural-language hiring brief, uses a Groq-hosted model to generate an editable search specification, filters the supplied candidate JSON deterministically, ranks the matching profiles with structured model output, accepts recruiter feedback, and repeats the process until the recruiter freezes a shortlist.

The backend deliberately does not use authentication, a production database, cross-session persistence, resume uploads, or multiple recruiter roles. Active workflow state is kept by LangGraph’s in-memory checkpointer for the duration of the local application process.

## Runtime Stack

- **FastAPI** exposes HTTP endpoints and validates request bodies.
- **Pydantic** validates candidate data, search filters, rubrics, feedback, scores, and model output.
- **LangGraph** orchestrates one interruptible workflow per search.
- **LangChain + ChatGroq** call the configured Groq model with strict JSON Schema output.
- **Python filtering service** applies hard constraints against the supplied JSON file.
- **In-memory checkpointing** resumes human-in-the-loop work using `search_id` as `thread_id`.

The default model is `openai/gpt-oss-20b`. Configure it through `GROQ_MODEL`. The preferred secret is `GROQ_API_KEY`; `GOOGLE_API_KEY` is still accepted as a compatibility fallback for existing local `.env` files.

## Directory Map

```text
backend/
  app/
    main.py                         FastAPI application factory and dependencies
    config.py                       Environment-backed settings
    api/searches.py                 Search endpoints and interrupt/resume handling
    models/candidate.py             Candidate and past-company schemas
    models/search.py                Filters, rubric, score, feedback, and API schemas
    services/candidate_repository.py Loads and validates the supplied JSON dataset
    services/filtering.py            Deterministic objective filtering
    ai/prompts.py                   Versioned parse, ranking, and refinement prompts
    ai/llm_service.py               ChatGroq client and structured model operations
    graph/state.py                  JSON-safe LangGraph state definition
    graph/workflow.py               Nodes, interrupts, routes, and checkpointed graph
  tests/
    test_filtering.py               Filtering behavior tests
    test_refinement_prompt.py       Overall-feedback regression test
```

The dataset is at the repository root: `profiles.json - Flexiple Engineering Challenge sample data`.

## Application Startup

`backend/app/main.py` creates the application through `create_app()`:

1. Load settings from `.env`.
2. Create a `CandidateRepository` for the supplied JSON file.
3. Create `LLMService`, which initializes `ChatGroq`.
4. Build one compiled LangGraph with an in-memory checkpointer.
5. Attach repository and graph instances to `app.state.dependencies`.
6. Register the search router and `/health` endpoint.

Run from the repository root:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

## LangGraph State

`RecruitmentState` is the shared JSON-safe state passed between nodes:

```text
search_id              Stable identifier and LangGraph thread_id
original_query         Recruiter’s initial free-text query
filters                Current ObjectiveFilters as a dictionary
rubric                 Current FitRubric as a dictionary
all_candidates         Complete validated dataset
filtered_candidates    Profiles that pass objective filters
ranked_results         CandidateScore objects sorted by score
diagnostics            Counts and reasons for filter exclusions
recruiter_feedback     Candidate-level feedback from the latest review
overall_feedback       Free-text recruiter guidance for refinement
refinement_round       Number of completed refinement cycles
changes                AI assumptions, warnings, or refinement changes
stage                  Current workflow stage
frozen                 Whether the recruiter finalized the search
error                  Optional surfaced workflow error
```

State stores dictionaries and lists rather than UI-formatted strings so it can be checkpointed, validated, reused in prompts, and serialized through the API.

## Workflow Nodes

The complete graph is implemented in `backend/app/graph/workflow.py`.

### `interpret_query`

Sends the recruiter query to Groq using `SearchSpec` JSON Schema output. The response contains objective filters, a subjective fit rubric, assumptions, and warnings. The graph then moves to human review.

### `review_spec`

Calls LangGraph `interrupt()` before doing any work that should not be repeated. The frontend receives the draft filters and rubric, allows direct editing, and resumes the graph with the approved values. Pydantic validates the resumed specification.

### `apply_objective_filters`

Converts state into validated `Candidate` and `ObjectiveFilters` models, then calls `filter_candidates()`. The LLM is not involved in this step. The node stores matched profiles and diagnostics.

If no profiles match, the conditional route goes back to `review_spec`. The frontend shows an empty-result warning so the recruiter can loosen the filters.

### `score_candidates`

Sends only profiles that passed objective filtering to Groq. Scoring uses three-profile batches, compact JSON, low reasoning effort, and a 2,048-token completion cap to fit free-tier Groq limits. The graph sorts scores descending and exposes the top 12 results to the recruiter.

Each score contains:

- `candidate_id`
- numeric score from 0 to 100
- strengths
- concerns
- concise explanation
- evidence references to profile fields

If a batch omits an expected candidate ID, valid scores are preserved and the missing profile receives a zero-score “unavailable” result rather than crashing the workflow.

### `review_results`

Pauses with an interrupt containing ranked candidates and diagnostics. The recruiter can submit candidate-level decisions (`accept`, `reject`, or `maybe`) plus overall free-text feedback.

The recruiter can also choose `freeze`, which marks the state as final, or `refine`, which routes to the refinement node.

### `refine_search_spec`

Sends the original query, current filters, current rubric, ranked results, candidate feedback, and overall feedback to Groq. It returns a complete replacement specification and a short change list. The workflow then returns to `review_spec`, ensuring the recruiter approves every AI-generated change.

### `prepare_final_summary`

Marks the search as frozen. The API exposes the final filters, rubric, visible ranked shortlist, candidate profiles, and refinement count.

## Prompt Design

Prompts are stored in `backend/app/ai/prompts.py` and are intentionally separated by task.

### Search interpretation

The interpretation prompt tells the model to distinguish hard requirements from preferences, use only fields represented in the dataset, avoid invented constraints, and surface ambiguity for recruiter review.

### Candidate ranking

The ranking prompt requires exact candidate IDs, evidence from real profile fields, concise explanations, and separate strengths and concerns. It explicitly allows a candidate to pass hard filters but still receive a lower subjective fit score.

### Refinement

The refinement prompt receives both candidate feedback and overall recruiter feedback. It must return a complete replacement specification, preserve approved constraints unless feedback justifies changing them, and explain meaningful changes.

All three calls use `with_structured_output(..., method="json_schema", strict=True)`. The resulting dictionaries are validated again with Pydantic before entering graph state.

## Deterministic Filtering

`backend/app/services/filtering.py` applies hard filters in this order:

1. Every required skill must match a candidate skill.
2. Experience must satisfy the inclusive minimum and maximum range.
3. Location must match an allowed location after normalization.
4. Current company type must match an allowed type.
5. Past-company keywords must appear in a past company’s name, type, or title.

Matching is case-insensitive. Bangalore and Bengaluru normalize to the same location. Preferred skills are retained in the search specification for the rubric but are not hard exclusions.

The filter service returns both matching candidates and `FilterDiagnostics`, including total profiles, matched count, excluded count, and the first exclusion reason recorded for each excluded profile.

## API Contract

### Start a search

```http
POST /api/searches
```

```json
{"query":"Backend engineers with PostgreSQL experience in Bangalore"}
```

The response normally contains `status: "interrupted"`, `interrupt.type: "review_spec"`, and the generated filters/rubric.

### Read a search

```http
GET /api/searches/{search_id}
```

Returns the current public state for reconnecting or inspecting the workflow.

### Resume specification review

```http
POST /api/searches/{search_id}/spec-review
```

The request contains the recruiter-approved `filters` and `rubric`. The graph resumes, filters candidates, scores them, and normally pauses at `review_results`.

### Resume result review

```http
POST /api/searches/{search_id}/result-review
```

Refinement request:

```json
{
  "action":"refine",
  "feedback":[{"candidate_id":"p01","decision":"reject","comment":"Too junior"}],
  "overall_feedback":"Prioritize startup ownership and Bangalore-based candidates."
}
```

Freeze request:

```json
{"action":"freeze","feedback":[],"overall_feedback":""}
```

## Error Handling

- **Invalid request data:** FastAPI/Pydantic returns `422`.
- **Groq quota/rate limit:** the API maps rate-limit failures to `429`.
- **Groq token-size failure:** oversized requests map to `413`; scoring is batched to reduce recurrence.
- **LLM scoring omissions:** missing candidate IDs receive an explicit unavailable score.
- **Empty result set:** the graph loops back to human filter review instead of returning fake candidates.
- **Unexpected AI/provider failure:** the endpoint logs the traceback and returns an actionable error response.

## Verification

```bash
python3 -m compileall -q backend
cd backend
pytest
```

For a manual end-to-end test, use the frontend or `http://localhost:8000/docs`: start a search, approve the specification, submit candidate feedback, refine once, approve the updated specification, and freeze the shortlist.

## Known Runtime Constraints

The current checkpointer is in-memory. Run one Uvicorn worker for local evaluation; multiple workers will not share active search state. Candidate scoring is intentionally limited to three-profile batches and a top-12 visible shortlist to keep Groq free-tier requests within practical token limits.
