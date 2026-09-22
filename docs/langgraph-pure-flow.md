# Pure LangGraph Workflow

This is the workflow-only view of the recruitment search. It excludes FastAPI, React, Groq, and the candidate repository so the graph control flow is easy to study.

```mermaid
flowchart TD
    START([START]) --> INTERPRET[interpret_query<br/>Generate SearchSpec]
    INTERPRET --> REVIEW_SPEC{{review_spec<br/>INTERRUPT<br/>Recruiter edits/approves filters + rubric}}
    REVIEW_SPEC --> FILTER[apply_objective_filters<br/>Deterministic filtering]
    FILTER --> HAS_MATCHES{filtered_candidates<br/>non-empty?}

    HAS_MATCHES -- No --> EMPTY[empty_results<br/>Keep diagnostics in state]
    EMPTY --> REVIEW_SPEC

    HAS_MATCHES -- Yes --> SCORE[score_candidates<br/>Batch scores + rank results]
    SCORE --> REVIEW_RESULTS{{review_results<br/>INTERRUPT<br/>Recruiter reviews candidates}}
    REVIEW_RESULTS --> ACTION{resume decision}

    ACTION -- refine --> STORE_FEEDBACK[Store candidate + overall feedback]
    STORE_FEEDBACK --> REFINE[refine_search_spec<br/>Generate replacement filters + rubric]
    REFINE --> REVIEW_SPEC

    ACTION -- freeze --> FREEZE[prepare_final_summary<br/>Mark state frozen]
    FREEZE --> END([END])

    classDef interrupt fill:#fff3df,stroke:#d99a42,color:#624717,stroke-width:2px;
    classDef ai fill:#edf5ff,stroke:#6b8fc7,color:#23416f;
    classDef human fill:#eef9f0,stroke:#73af82,color:#255f36;
    classDef route fill:#f7f7f7,stroke:#9ba6a0,color:#37443c;

    class INTERPRET,SCORE,REFINE ai;
    class REVIEW_SPEC,REVIEW_RESULTS interrupt;
    class STORE_FEEDBACK,FREEZE human;
    class HAS_MATCHES,ACTION route;
```

## State Movement

```text
original_query
    → filters + rubric
    → recruiter-approved filters + rubric
    → filtered_candidates + diagnostics
    → ranked_results
    → recruiter_feedback
    → replacement filters + rubric
    → frozen final state
```

## Important LangGraph Behavior

- `review_spec` pauses before filtering so the recruiter owns the search specification.
- `review_results` pauses before deciding whether to refine or freeze.
- Resuming `review_spec` routes back through filtering and scoring.
- Resuming `review_results` with `refine` loops through feedback and returns to `review_spec`.
- Resuming `review_results` with `freeze` routes to `prepare_final_summary` and then ends.
- An empty result set is a normal route back to `review_spec`, not a terminal failure.
- Each search uses one LangGraph `thread_id`, allowing interrupt state to resume across HTTP requests.
