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


SCORE_BATCH_SIZE = 3


class LLMService:
    def __init__(self, settings: Settings):
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is required for Groq workflow operations")
        from langchain_groq import ChatGroq

        self.llm = ChatGroq(
            model=settings.groq_model,
            temperature=settings.llm_temperature,
            api_key=settings.groq_api_key,
            max_tokens=2048,
            reasoning_effort="low",
            max_retries=2,
        )

    def parse_search(self, query: str) -> SearchSpec:
        structured_llm = self.llm.with_structured_output(
            schema=SearchSpec.model_json_schema(),
            method="json_schema",
            strict=True,
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
        all_scores = []
        for start in range(0, len(candidates), SCORE_BATCH_SIZE):
            batch = candidates[start : start + SCORE_BATCH_SIZE]
            all_scores.extend(self._score_candidate_batch(filters, rubric, batch).scores)
        return CandidateScoreBatch(scores=all_scores)

    def _score_candidate_batch(
        self,
        filters: ObjectiveFilters,
        rubric: FitRubric,
        candidates: list[Candidate],
    ) -> CandidateScoreBatch:
        structured_llm = self.llm.with_structured_output(
            schema=CandidateScoreBatch.model_json_schema(),
            method="json_schema",
            strict=True,
        )
        response = structured_llm.invoke([
            ("system", SCORE_CANDIDATES_SYSTEM_PROMPT),
            (
                "human",
                SCORE_CANDIDATES_USER_PROMPT.format(
                    filters=filters.model_dump_json(),
                    rubric=rubric.model_dump_json(),
                    candidates=json.dumps(
                        [candidate.model_dump() for candidate in candidates],
                        separators=(",", ":"),
                    ),
                    candidate_ids=json.dumps([candidate.id for candidate in candidates]),
                ),
            ),
        ])
        validated = CandidateScoreBatch.model_validate(response)
        expected_ids = {candidate.id for candidate in candidates}
        scores_by_id = {
            score.candidate_id: score
            for score in validated.scores
            if score.candidate_id in expected_ids
        }
        recovered_scores = [scores_by_id[candidate.id] for candidate in candidates if candidate.id in scores_by_id]
        for candidate in candidates:
            if candidate.id not in scores_by_id:
                recovered_scores.append(
                    {
                        "candidate_id": candidate.id,
                        "score": 0,
                        "strengths": [],
                        "concerns": ["The model did not return a valid score for this profile."],
                        "explanation": "Scoring was unavailable for this profile. Review the source profile manually.",
                        "evidence": [],
                    }
                )
        return CandidateScoreBatch.model_validate({"scores": recovered_scores})

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
            strict=True,
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
