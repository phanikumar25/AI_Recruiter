import re

from app.models.candidate import Candidate
from app.models.search import FilterDiagnostics, ObjectiveFilters


LOCATION_ALIASES = {
    "bangalore": "bengaluru",
    "bengaluru": "bengaluru",
}


def normalize(value: str) -> str:
    value = re.sub(r"[^a-z0-9+#.]+", " ", value.casefold())
    return " ".join(value.split())


def normalize_location(value: str) -> str:
    normalized = normalize(value)
    return LOCATION_ALIASES.get(normalized, normalized)


def contains_skill(candidate_skills: list[str], required_skill: str) -> bool:
    requested = normalize(required_skill)
    return any(normalize(skill) == requested for skill in candidate_skills)


def matches_candidate(candidate: Candidate, filters: ObjectiveFilters) -> tuple[bool, str | None]:
    if filters.required_skills:
        missing = [skill for skill in filters.required_skills if not contains_skill(candidate.skills, skill)]
        if missing:
            return False, "required_skills"

    if filters.min_years_experience is not None and candidate.years_experience < filters.min_years_experience:
        return False, "minimum_experience"

    if filters.max_years_experience is not None and candidate.years_experience > filters.max_years_experience:
        return False, "maximum_experience"

    if filters.locations:
        allowed_locations = {normalize_location(location) for location in filters.locations}
        if normalize_location(candidate.location) not in allowed_locations:
            return False, "location"

    if filters.company_types:
        allowed_types = {normalize(value) for value in filters.company_types}
        if normalize(candidate.current_company_type) not in allowed_types:
            return False, "company_type"

    if filters.past_company_keywords:
        past_text = " ".join(
            f"{company.company} {company.company_type} {company.title}"
            for company in candidate.past_companies
        )
        normalized_past_text = normalize(past_text)
        if not any(normalize(keyword) in normalized_past_text for keyword in filters.past_company_keywords):
            return False, "past_company"

    return True, None


def filter_candidates(
    candidates: list[Candidate], filters: ObjectiveFilters
) -> tuple[list[Candidate], FilterDiagnostics]:
    matched: list[Candidate] = []
    exclusion_reasons: dict[str, int] = {}

    for candidate in candidates:
        is_match, reason = matches_candidate(candidate, filters)
        if is_match:
            matched.append(candidate)
        elif reason:
            exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1

    diagnostics = FilterDiagnostics(
        total_candidates=len(candidates),
        matched_candidates=len(matched),
        excluded_candidates=len(candidates) - len(matched),
        exclusion_reasons=exclusion_reasons,
    )
    return matched, diagnostics
