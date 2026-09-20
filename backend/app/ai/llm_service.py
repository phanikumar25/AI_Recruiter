import json

from app.ai.prompts import (
    PARSE_SEARCH_SYSTEM_PROMPT,
    PARSE_SEARCH_USER_PROMPT,
    REFINE_SEARCH_SYSTEM_PROMPT,
    REFINE_SEARCH_USER_PROMPT,
    SCORE_CANDIDATES_SYSTEM_PROMPT,
    SCORE_CANDIDATES_USER_PROMPT,
)
from app.config import Settings
from app.models.candidate import Candidate
from app.models.search import (
    CandidateScoreBatch,
    FitRubric,
    ObjectiveFilters,
    RefinementResult,
    SearchSpec,
)


class LLMService:
    def __init__(self, settings: Settings):
        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for Gemini workflow operations")
        from langchain_google_genai import ChatGoogleGenerativeAI

        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=settings.llm_temperature,
            google_api_key=settings.google_api_key,
            max_retries=2,
        )

    def parse_search(self, query: str) -> SearchSpec:
        structured_llm = self.llm.with_structured_output(
            schema=SearchSpec.model_json_schema(),
            method="json_schema",
        )
        response = structured_llm.invoke([
            ("system", PARSE_SEARCH_SYSTEM_PROMPT),
            ("human", PARSE_SEARCH_USER_PROMPT.format(query=query)),
        ])
        return SearchSpec.model_validate(response)

    def score_candidates(
        self,
        filters: ObjectiveFilters,
        rubric: FitRubric,
        candidates: list[Candidate],
    ) -> CandidateScoreBatch:
        rubric = FitRubric.model_validate(rubric)
        structured_llm = self.llm.with_structured_output(
            schema=CandidateScoreBatch.model_json_schema(),
            method="json_schema",
        )
        response = structured_llm.invoke([
            ("system", SCORE_CANDIDATES_SYSTEM_PROMPT),
            (
                "human",
                SCORE_CANDIDATES_USER_PROMPT.format(
                    filters=filters.model_dump_json(indent=2),
                    rubric=rubric.model_dump_json(indent=2),
                    candidates=json.dumps(
                        [candidate.model_dump() for candidate in candidates],
                        indent=2,
                    ),
                ),
            ),
        ])
        validated = CandidateScoreBatch.model_validate(response)
        expected_ids = {candidate.id for candidate in candidates}
        actual_ids = {score.candidate_id for score in validated.scores}
        if actual_ids != expected_ids:
            raise ValueError("LLM scoring response did not contain exactly the supplied candidate IDs")
        return validated

    def refine_search(
        self,
        original_query: str,
        filters: ObjectiveFilters,
        rubric: FitRubric,
        results: list[dict],
        feedback: list[dict],
        overall_feedback: str = "",
    ) -> RefinementResult:
        rubric = FitRubric.model_validate(rubric)
        structured_llm = self.llm.with_structured_output(
            schema=RefinementResult.model_json_schema(),
            method="json_schema",
        )
        response = structured_llm.invoke([
            ("system", REFINE_SEARCH_SYSTEM_PROMPT),
            (
                "human",
                REFINE_SEARCH_USER_PROMPT.format(
                    original_query=original_query,
                    filters=filters.model_dump_json(indent=2),
                    rubric=rubric.model_dump_json(indent=2),
                    results=json.dumps(results, indent=2),
                    feedback=json.dumps(feedback, indent=2),
                    overall_feedback=overall_feedback,
                ),
            ),
        ])
        return RefinementResult.model_validate(response)
