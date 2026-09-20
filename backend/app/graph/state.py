from typing import TypedDict


class RecruitmentState(TypedDict, total=False):
    search_id: str
    original_query: str
    filters: dict | None
    rubric: dict | None
    all_candidates: list[dict]
    filtered_candidates: list[dict]
    ranked_results: list[dict]
    diagnostics: dict | None
    recruiter_feedback: list[dict]
    overall_feedback: str
    refinement_round: int
    changes: list[str]
    stage: str
    frozen: bool
    error: str | None
