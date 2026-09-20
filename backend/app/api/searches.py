import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from langgraph.types import Command

from app.models.candidate import Candidate
from app.models.search import (
    CandidateScore,
    FilterDiagnostics,
    ObjectiveFilters,
    PublicSearchState,
    RubricCriterion,
    FitRubric,
    ResultsReviewRequest,
    SearchCreateRequest,
    SpecReviewRequest,
)
from app.services.candidate_repository import CandidateRepository


router = APIRouter(prefix="/api/searches", tags=["searches"])
logger = logging.getLogger(__name__)


def graph_config(search_id: str) -> dict:
    return {"configurable": {"thread_id": search_id}}


async def get_state(graph, search_id: str):
    return await graph.aget_state(graph_config(search_id))


def interrupt_value(result: dict) -> dict | None:
    interrupts = result.get("__interrupt__", ())
    if not interrupts:
        return None
    return interrupts[0].value


def public_state(search_id: str, values: dict) -> PublicSearchState:
    filters = ObjectiveFilters.model_validate(values["filters"]) if values.get("filters") else None
    rubric = FitRubric.model_validate(values["rubric"]) if values.get("rubric") else None
    diagnostics = (
        FilterDiagnostics.model_validate(values["diagnostics"])
        if values.get("diagnostics")
        else None
    )
    return PublicSearchState(
        search_id=search_id,
        stage=values.get("stage", "unknown"),
        original_query=values.get("original_query", ""),
        filters=filters,
        rubric=rubric,
        candidate_profiles=[
            Candidate.model_validate(item)
            for item in values.get("filtered_candidates", [])
        ],
        results=[CandidateScore.model_validate(item) for item in values.get("ranked_results", [])],
        diagnostics=diagnostics,
        refinement_round=values.get("refinement_round", 0),
        changes=values.get("changes", []),
        frozen=values.get("frozen", False),
        error=values.get("error"),
    )


async def response_from_run(graph, search_id: str, result: dict) -> dict:
    checkpoint = await get_state(graph, search_id)
    state = public_state(search_id, checkpoint.values)
    return {
        "status": "interrupted" if interrupt_value(result) else "completed",
        "interrupt": interrupt_value(result),
        "state": state.model_dump(),
    }


def get_dependencies(request: Request):
    return request.app.state.dependencies


def is_rate_limit_error(error: Exception) -> bool:
    return error.__class__.__name__ == "GoogleRateLimitError" or "429" in str(error)


@router.post("")
async def create_search(payload: SearchCreateRequest, request: Request):
    dependencies = get_dependencies(request)
    search_id = f"search_{uuid4().hex}"
    candidates = dependencies.repository.all()
    initial_state = {
        "search_id": search_id,
        "original_query": payload.query,
        "all_candidates": [candidate.model_dump() for candidate in candidates],
        "refinement_round": 0,
        "frozen": False,
        "stage": "interpreting_query",
    }
    try:
        result = await dependencies.graph.ainvoke(initial_state, graph_config(search_id))
        return await response_from_run(dependencies.graph, search_id, result)
    except Exception as exc:
        logger.exception("Failed to start search %s", search_id)
        status_code = 429 if is_rate_limit_error(exc) else 502
        detail = (
            "Gemini quota exceeded. Set GEMINI_MODEL to a model available to your API key "
            "or wait for the quota window to reset."
            if status_code == 429
            else f"Unable to interpret search: {exc}"
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/{search_id}")
async def read_search(search_id: str, request: Request):
    dependencies = get_dependencies(request)
    try:
        checkpoint = await get_state(dependencies.graph, search_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Search session not found") from exc
    if not checkpoint.values:
        raise HTTPException(status_code=404, detail="Search session not found")
    return {"state": public_state(search_id, checkpoint.values).model_dump()}


@router.post("/{search_id}/spec-review")
async def resume_spec_review(
    search_id: str,
    payload: SpecReviewRequest,
    request: Request,
):
    dependencies = get_dependencies(request)
    try:
        result = await dependencies.graph.ainvoke(
            Command(resume=payload.model_dump()),
            graph_config(search_id),
        )
        return await response_from_run(dependencies.graph, search_id, result)
    except Exception as exc:
        logger.exception("Failed to resume specification review for %s", search_id)
        status_code = 429 if is_rate_limit_error(exc) else 422
        raise HTTPException(status_code=status_code, detail=f"Unable to resume specification review: {exc}") from exc


@router.post("/{search_id}/result-review")
async def resume_result_review(
    search_id: str,
    payload: ResultsReviewRequest,
    request: Request,
):
    dependencies = get_dependencies(request)
    try:
        result = await dependencies.graph.ainvoke(
            Command(resume=payload.model_dump()),
            graph_config(search_id),
        )
        return await response_from_run(dependencies.graph, search_id, result)
    except Exception as exc:
        logger.exception("Failed to process result review for %s", search_id)
        status_code = 429 if is_rate_limit_error(exc) else 422
        raise HTTPException(status_code=status_code, detail=f"Unable to process recruiter feedback: {exc}") from exc
