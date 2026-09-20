# Frontend

The frontend is a React + TypeScript recruiter workspace for the interruptible FastAPI/LangGraph search workflow.

## Run locally

From the repository root:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The app expects the backend at `http://localhost:8000`. Set `VITE_API_BASE_URL` if the backend runs elsewhere.

## Recruiter flow

1. Enter a natural-language search brief.
2. Review and edit the generated objective filters and fit rubric.
3. Review ranked candidates and evidence-backed explanations.
4. Mark candidates as good matches, not a fit, or maybe.
5. Add overall feedback to refine the search.
6. Approve the updated specification and repeat as needed.
7. Freeze the final shortlist.
