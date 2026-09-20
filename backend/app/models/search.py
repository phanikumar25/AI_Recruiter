from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .candidate import Candidate


class ObjectiveFilters(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_years_experience: float | None = Field(default=None, ge=0)
    max_years_experience: float | None = Field(default=None, ge=0)
    locations: list[str] = Field(default_factory=list)
    company_types: list[str] = Field(default_factory=list)
    past_company_keywords: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_experience_range(self) -> "ObjectiveFilters":
        if (
            self.min_years_experience is not None
            and self.max_years_experience is not None
            and self.min_years_experience > self.max_years_experience
        ):
            raise ValueError("Minimum experience cannot exceed maximum experience")
        return self


class RubricCriterion(BaseModel):
    name: str
    description: str
    weight: float = Field(gt=0, le=1)


class FitRubric(BaseModel):
    criteria: list[RubricCriterion] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_weights(self) -> "FitRubric":
        if sum(item.weight for item in self.criteria) <= 0:
            raise ValueError("Rubric weights must have a positive total")
        return self


class SearchSpec(BaseModel):
    filters: ObjectiveFilters
    rubric: FitRubric
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CandidateScore(BaseModel):
    candidate_id: str
    score: float = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    explanation: str
    evidence: list[str] = Field(default_factory=list)


class CandidateScoreBatch(BaseModel):
    scores: list[CandidateScore]


class RefinementResult(BaseModel):
    filters: ObjectiveFilters
    rubric: FitRubric
    changes: list[str] = Field(default_factory=list)


class RecruiterFeedback(BaseModel):
    candidate_id: str
    decision: Literal["accept", "reject", "maybe"]
    comment: str = ""


class SearchCreateRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)


class SpecReviewRequest(BaseModel):
    filters: ObjectiveFilters
    rubric: FitRubric


class ResultsReviewRequest(BaseModel):
    action: Literal["refine", "freeze"]
    feedback: list[RecruiterFeedback] = Field(default_factory=list)
    overall_feedback: str = Field(default="", max_length=4000)


class FilterDiagnostics(BaseModel):
    total_candidates: int
    matched_candidates: int
    excluded_candidates: int
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)


class PublicSearchState(BaseModel):
    search_id: str
    stage: str
    original_query: str
    filters: ObjectiveFilters | None = None
    rubric: FitRubric | None = None
    results: list[CandidateScore] = Field(default_factory=list)
    diagnostics: FilterDiagnostics | None = None
    refinement_round: int = 0
    changes: list[str] = Field(default_factory=list)
    frozen: bool = False
    error: str | None = None


def candidate_from_state(value: dict) -> Candidate:
    return Candidate.model_validate(value)
