# LangGraph Architecture

This diagram describes one LangGraph workflow for one recruiter search session. The graph pauses at human-review nodes and resumes with the same `thread_id`, so filters, rubric edits, candidate feedback, and refinement rounds remain part of one stateful flow.

```mermaid
flowchart TD
    Start([Recruiter submits free-text search]) --> Interpret[interpret_query<br/>LLM + structured SearchSpec<br/>No deterministic filtering yet]
    Interpret --> ReviewSpec{{human_review_spec<br/>INTERRUPT<br/>Recruiter edits filters and rubric}}
    ReviewSpec --> Apply[apply_objective_filters<br/>Pure Python against supplied JSON<br/>Required filters are hard constraints]
    Apply --> Empty{Any candidates left?}
    Empty -- No --> EmptyReview[Show empty-result diagnostics<br/>Loop back so recruiter can loosen filters]
    EmptyReview --> ReviewSpec
    Empty -- Yes --> Score[score_candidates<br/>LLM sees only filtered profiles<br/>Must cite actual profile fields]
    Score --> Results{{human_review_results<br/>INTERRUPT<br/>Recruiter accepts/rejects/maybe + comments}}
    Results --> Decision{Recruiter action}
    Decision -- Freeze --> Summary[prepare_final_summary\nFreeze filters, rubric, and ranked shortlist]
    Summary --> End([Frozen search])
    Decision -- Refine --> Refine[refine_search_spec<br/>LLM considers current spec + feedback<br/>Returns complete replacement spec]
    Refine --> Validate[validate_search_spec<br/>Pydantic validation<br/>Reject invalid ranges/weights]
    Validate --> ReviewSpec

    CandidateData[(profiles.json<br/>Entire supplied talent pool)] -. loaded at start .-> Apply
    LLM[(Server-side LLM<br/>API key from environment)] -. parse / score / refine .-> Interpret
    LLM -.-> Score
    LLM -.-> Refine
    Checkpoint[(LangGraph checkpointer\nthread_id = search_id)] -. saves at interrupts .-> ReviewSpec
    Checkpoint -. resumes after HTTP request .-> Results
```

## Reading the Flow

- The LLM interprets the recruiter’s language, but application code applies objective filters. This keeps facts such as location, experience, and skills deterministic.
- The first interrupt is an approval boundary. The recruiter owns the final filters and rubric before candidates are scored.
- Ranking is subjective and LLM-assisted, but every explanation must cite evidence from the candidate JSON.
- Feedback creates a loop. The LLM proposes changes, and the recruiter gets another approval opportunity before the next run.
- Empty results are a normal branch, not an exception. The recruiter can adjust the specification and try again.
- Freezing ends the graph and produces the final state required by the assignment.
