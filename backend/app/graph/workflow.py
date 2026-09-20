from typing import Any

try:
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver as InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.ai.llm_service import LLMService
from app.graph.state import RecruitmentState
from app.models.candidate import Candidate
from app.models.search import (
    CandidateScoreBatch,
    ObjectiveFilters,
    RecruiterFeedback,
    RefinementResult,
    SearchSpec,
)
from app.services.filtering import filter_candidates


def build_graph(llm_service: LLMService):
    def interpret_query(state: RecruitmentState) -> dict[str, Any]:
        specification = llm_service.parse_search(state["original_query"])
        return {
            "filters": specification.filters.model_dump(),
            "rubric": specification.rubric.model_dump(),
            "changes": specification.assumptions + specification.warnings,
            "stage": "review_spec",
            "error": None,
        }

    def review_spec(state: RecruitmentState) -> dict[str, Any]:
        decision = interrupt(
            {
                "type": "review_spec",
                "message": "Review and approve the generated filters and rubric.",
                "filters": state["filters"],
                "rubric": state["rubric"],
                "diagnostics": state.get("diagnostics"),
                "changes": state.get("changes", []),
            }
        )
        specification = SearchSpec(
            filters=decision["filters"],
            rubric=decision["rubric"],
        )
        return {
            "filters": specification.filters.model_dump(),
            "rubric": specification.rubric.model_dump(),
            "stage": "filtering",
            "error": None,
        }

    def apply_objective_filters(state: RecruitmentState) -> dict[str, Any]:
        filters = ObjectiveFilters.model_validate(state["filters"])
        candidates = [Candidate.model_validate(item) for item in state["all_candidates"]]
        matched, diagnostics = filter_candidates(candidates, filters)
        return {
            "filtered_candidates": [candidate.model_dump() for candidate in matched],
            "diagnostics": diagnostics.model_dump(),
            "stage": "scoring" if matched else "empty_results",
        }

    def route_after_filtering(state: RecruitmentState) -> str:
        return "score_candidates" if state.get("filtered_candidates") else "review_spec"

    def score_candidates(state: RecruitmentState) -> dict[str, Any]:
        filters = ObjectiveFilters.model_validate(state["filters"])
        rubric = SearchSpec(filters=filters, rubric=state["rubric"]).rubric
        candidates = [Candidate.model_validate(item) for item in state["filtered_candidates"]]
        scores = llm_service.score_candidates(
            filters,
            rubric,
            candidates,
        )
        ranked = sorted(scores.scores, key=lambda score: score.score, reverse=True)
        return {
            "ranked_results": [score.model_dump() for score in ranked],
            "stage": "review_results",
            "error": None,
        }

    def review_results(state: RecruitmentState) -> dict[str, Any]:
        decision = interrupt(
            {
                "type": "review_results",
                "message": "Review candidates and choose refinement or freeze.",
                "results": state.get("ranked_results", []),
                "diagnostics": state.get("diagnostics"),
                "refinement_round": state.get("refinement_round", 0),
            }
        )
        if decision["action"] == "freeze":
            return {"stage": "freezing", "frozen": True}

        feedback = [RecruiterFeedback.model_validate(item) for item in decision.get("feedback", [])]
        return {
            "recruiter_feedback": [item.model_dump() for item in feedback],
            "overall_feedback": decision.get("overall_feedback", ""),
            "stage": "refining",
        }

    def route_after_results(state: RecruitmentState) -> str:
        return "prepare_final_summary" if state.get("frozen") else "refine_search_spec"

    def refine_search_spec(state: RecruitmentState) -> dict[str, Any]:
        filters = ObjectiveFilters.model_validate(state["filters"])
        rubric = SearchSpec(filters=filters, rubric=state["rubric"]).rubric
        result = llm_service.refine_search(
            state["original_query"],
            filters,
            rubric,
            state.get("ranked_results", []),
            state.get("recruiter_feedback", []),
            state.get("overall_feedback", ""),
        )
        refinement = RefinementResult.model_validate(result)
        return {
            "filters": refinement.filters.model_dump(),
            "rubric": refinement.rubric.model_dump(),
            "changes": refinement.changes,
            "refinement_round": state.get("refinement_round", 0) + 1,
            "stage": "review_spec",
        }

    def prepare_final_summary(state: RecruitmentState) -> dict[str, Any]:
        return {"stage": "frozen", "frozen": True}

    graph_builder = StateGraph(RecruitmentState)
    graph_builder.add_node("interpret_query", interpret_query)
    graph_builder.add_node("review_spec", review_spec)
    graph_builder.add_node("apply_objective_filters", apply_objective_filters)
    graph_builder.add_node("score_candidates", score_candidates)
    graph_builder.add_node("review_results", review_results)
    graph_builder.add_node("refine_search_spec", refine_search_spec)
    graph_builder.add_node("prepare_final_summary", prepare_final_summary)

    graph_builder.add_edge(START, "interpret_query")
    graph_builder.add_edge("interpret_query", "review_spec")
    graph_builder.add_edge("review_spec", "apply_objective_filters")
    graph_builder.add_conditional_edges(
        "apply_objective_filters",
        route_after_filtering,
        {
            "score_candidates": "score_candidates",
            "review_spec": "review_spec",
        },
    )
    graph_builder.add_edge("score_candidates", "review_results")
    graph_builder.add_conditional_edges(
        "review_results",
        route_after_results,
        {
            "refine_search_spec": "refine_search_spec",
            "prepare_final_summary": "prepare_final_summary",
        },
    )
    graph_builder.add_edge("refine_search_spec", "review_spec")
    graph_builder.add_edge("prepare_final_summary", END)

    return graph_builder.compile(checkpointer=InMemorySaver())
