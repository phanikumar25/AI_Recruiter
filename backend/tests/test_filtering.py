from app.models.candidate import Candidate
from app.models.search import ObjectiveFilters
from app.services.filtering import filter_candidates


def candidate(**overrides) -> Candidate:
    data = {
        "id": "p01",
        "name": "Test Candidate",
        "current_title": "Backend Engineer",
        "years_experience": 4,
        "location": "Bangalore",
        "current_company": "Example",
        "current_company_type": "startup",
        "skills": ["Node.js", "PostgreSQL", "AWS RDS"],
        "past_companies": [],
        "education": "B.Tech",
        "summary": "Backend engineer",
    }
    data.update(overrides)
    return Candidate.model_validate(data)


def test_filters_required_skills_and_bangalore_alias():
    matched, diagnostics = filter_candidates(
        [candidate()],
        ObjectiveFilters(
            required_skills=["PostgreSQL"],
            locations=["Bengaluru"],
            min_years_experience=1,
            max_years_experience=4,
            company_types=["startup"],
        ),
    )

    assert [item.id for item in matched] == ["p01"]
    assert diagnostics.matched_candidates == 1


def test_required_skills_are_all_required():
    matched, diagnostics = filter_candidates(
        [candidate()],
        ObjectiveFilters(required_skills=["PostgreSQL", "Python"]),
    )

    assert matched == []
    assert diagnostics.exclusion_reasons["required_skills"] == 1


def test_filter_matches_past_company_text():
    profile = candidate(
        past_companies=[
            {
                "company": "Freshworks",
                "company_type": "scaleup",
                "title": "Backend Engineer",
                "years": 2,
            }
        ]
    )
    matched, _ = filter_candidates(
        [profile],
        ObjectiveFilters(past_company_keywords=["Freshworks"]),
    )

    assert [item.id for item in matched] == ["p01"]
