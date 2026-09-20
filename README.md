# Scoutwise — AI Recruitment Sourcing Loop

Scoutwise is a focused full-stack implementation of the Flexiple Engineering Hiring Challenge. It helps a recruiter turn a free-text hiring brief into editable search filters and a fit rubric, rank matching profiles with Groq-hosted models, provide feedback, refine the search, and freeze a final shortlist.

## Assignment Coverage

- Free-text recruiter search interpreted into structured objective filters and a subjective fit rubric.
- Human review before the first candidate search and after every refinement round.
- Deterministic filtering against the supplied fictional candidate dataset.
- Groq-hosted model scoring and ranking with explanations grounded in actual profile fields.
- Recruiter feedback at both candidate and overall-search level.
- Repeated refinement loop and frozen final filters, rubric, and shortlist.
- Loading, empty-result, error, rate-limit, and recovery states.

The application intentionally does not include login, multiple roles, cross-session persistence, resume uploads, a production database, or features outside the sourcing refinement loop, matching the challenge scope.

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer and npm
- A GroqCloud API key

The default model is `openai/gpt-oss-20b` hosted by Groq, configurable through `GROQ_MODEL`. Model availability and quotas are controlled by Groq.

## Quick Start

### 1. Configure the backend

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp backend/.env.example .env
```

Edit `.env` and set:

```env
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-20b
```

Start FastAPI:

```bash
uvicorn app.main:app --app-dir backend --reload
```

The backend runs at `http://localhost:8000`. Verify it with `http://localhost:8000/health` or inspect the API through `http://localhost:8000/docs`.

### 2. Configure the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend runs at `http://localhost:5173` and expects FastAPI at `http://localhost:8000`. Change `VITE_API_BASE_URL` in `frontend/.env` if the backend uses another URL.

## Evaluator Walkthrough

1. Open `http://localhost:5173`.
2. Enter:
   ```text
   Backend developers with 1-4 years of experience who have worked at startups, based in Bangalore, with PostgreSQL experience.
   ```
3. Review the generated filters and rubric. Edit them if desired, then select **Run against talent map**.
4. Review candidate scores, evidence, strengths, and concerns.
5. Mark at least one candidate as **Good match** and one as **Not for me**.
6. Add overall feedback such as:
   ```text
   Only show candidates based in Bangalore and prioritize startup ownership over years of experience.
   ```
7. Select **Refine with this signal**, review the updated filters/rubric, and run the next round.
8. Select **Freeze this shortlist** to view the final filters, rubric, and ranked shortlist.

## Demonstrating Error Handling

### Empty results

After the AI generates a specification, edit it to use `Reykjavik`, `COBOL`, or a minimum of `20` years of experience. The deterministic filter returns no profiles and the UI offers a way to loosen the specification.

### Invalid filters

Set minimum experience higher than maximum experience, such as `8` and `3`. Pydantic validation returns a `422` response and the frontend displays an actionable error.

### Backend failure

Stop FastAPI while the frontend is open and submit a search. The UI displays a recovery error while preserving the recruiter’s input.

### Groq quota failure

If the selected Groq model has no quota or the request exceeds its TPM limit, the backend returns a clear quota message rather than hiding the failure behind a generic server error. Use `GROQ_MODEL=openai/gpt-oss-20b`; candidate scoring is also batched into small requests and the refinement prompt uses only the visible shortlist.

## Architecture

The backend uses one LangGraph workflow per search session. It checkpoints using `search_id` and pauses with `interrupt()` at the two human-review points:

```text
free-text query
  → Groq structured search specification
  → recruiter edits/approves filters and rubric
  → deterministic local filtering
  → Groq candidate scoring
  → recruiter candidate and overall feedback
  → Groq refinement loop
  → frozen shortlist
```

The annotated workflow diagram is in [`docs/langgraph-architecture.md`](docs/langgraph-architecture.md). Backend prompts are kept in [`backend/app/ai/prompts.py`](backend/app/ai/prompts.py), and the graph orchestration is in [`backend/app/graph/workflow.py`](backend/app/graph/workflow.py).

Objective filters are never delegated to the LLM after generation. Python applies skills, experience, location aliases such as Bangalore/Bengaluru, company type, and past-company constraints against `profiles.json - Flexiple Engineering Challenge sample data`. The Groq-hosted model only interprets the query, scores candidates who pass those filters, and proposes refinements.

## Project Structure

```text
backend/app/       FastAPI routes, Pydantic models, filtering, prompts, LangGraph
backend/tests/     Backend filtering and prompt tests
frontend/src/      React recruiter workspace and API client
docs/              LangGraph architecture diagram
profiles.json ...  Supplied candidate talent pool
```

## Verification

Backend syntax and tests:

```bash
python3 -m compileall -q backend
cd backend
pytest
```

Frontend production build:

```bash
cd frontend
npm run build
```

## Design Decisions

- Groq strict structured JSON Schema output keeps filters, rubrics, scores, and refinements validated.
- Candidate filtering is deterministic so explanations are based on real supplied data.
- In-memory LangGraph checkpointing is sufficient for the assignment because cross-session persistence is explicitly out of scope.
- The frontend keeps the recruiter in control: AI suggestions are always visible and editable before execution.
