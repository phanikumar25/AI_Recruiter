# Backend

The backend is a FastAPI service with one LangGraph workflow per recruitment search. LangGraph checkpoints each search by `search_id`; the workflow pauses with `interrupt()` when the recruiter must review a generated specification or candidate results.

## Run locally

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp backend/.env.example .env
# Set GROQ_API_KEY in .env
uvicorn app.main:app --app-dir backend --reload
```

The service exposes `GET /health` and search workflow routes under `/api/searches`.

## Workflow contract

`POST /api/searches` starts the graph and normally returns a `review_spec` interrupt. The frontend edits or accepts the filters and rubric, then posts them to `/{search_id}/spec-review`. Once candidates are scored, the graph returns a `review_results` interrupt. The frontend posts candidate feedback to `/{search_id}/result-review` to either refine the search or freeze it.

## AI boundaries

- `parse_search` converts free text into a validated `SearchSpec`.
- `apply_objective_filters` is deterministic Python logic over the supplied JSON dataset.
- `score_candidates` receives only candidates that passed objective filters and must return evidence-backed scores.
- Candidate scoring is split into three-profile batches with concise outputs and low reasoning effort so free-tier Groq TPM limits are not exceeded.
- `refine_search` returns a complete replacement specification based on recruiter feedback.

Prompt templates live in `app/ai/prompts.py` so they are versioned and reviewable. The frontend should render the interrupt payload rather than infer workflow state from individual fields.

## Verification

```bash
cd backend
pytest
```

The current test suite covers required-skill matching, location aliases, experience constraints, and past-company filtering. Install dependencies before running it.
