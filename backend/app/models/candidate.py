from pydantic import BaseModel, Field


class PastCompany(BaseModel):
    company: str
    company_type: str
    title: str
    years: float = Field(ge=0)


class Candidate(BaseModel):
    id: str
    name: str
    current_title: str
    years_experience: float = Field(ge=0)
    location: str
    current_company: str
    current_company_type: str
    skills: list[str]
    past_companies: list[PastCompany]
    education: str
    summary: str
