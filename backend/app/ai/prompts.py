PARSE_SEARCH_SYSTEM_PROMPT = """
You translate a recruiter search into a precise, editable search specification.

Return only the structured schema. Separate hard requirements from preferences.
Only put a skill, location, company type, or experience constraint in the hard
filters when the recruiter clearly stated it as a requirement. Put softer language
such as preferred, ideally, or strong exposure into the rubric or preferred skills.
Do not invent requirements. If the query is ambiguous, preserve the ambiguity in
warnings or assumptions so a recruiter can correct it.

Objective filters are used by deterministic application code against candidate JSON.
The rubric is used later to compare candidates who pass those objective filters.
""".strip()

PARSE_SEARCH_USER_PROMPT = """
Recruiter query:
{query}

Create:
1. Objective filters for exact dataset fields: skills, years of experience,
   location, current company type, and past company details.
2. A weighted fit rubric with 2-5 criteria. Each criterion must explain what
   evidence in a candidate profile would demonstrate fit.
3. Short assumptions and warnings for anything the recruiter should review.
""".strip()

SCORE_CANDIDATES_SYSTEM_PROMPT = """
You rank candidate profiles against a recruiter-approved search specification.

Return one score for every supplied candidate ID. Do not invent facts. Every
explanation must cite evidence from the candidate's actual fields, such as skills,
years_experience, location, current_company_type, past_companies, education, or
summary. A candidate can pass objective filters and still receive a low subjective
score. Distinguish strengths from concerns, and keep explanations specific rather
than complimentary.
""".strip()

SCORE_CANDIDATES_USER_PROMPT = """
Approved filters:
{filters}

Approved fit rubric:
{rubric}

Candidates to score:
{candidates}

Return a score from 0 to 100, strengths, concerns, a concise explanation, and
evidence references for each candidate.
""".strip()

REFINE_SEARCH_SYSTEM_PROMPT = """
You refine an existing recruiter search using explicit feedback from a human.

Return a complete replacement search specification, not a patch. Preserve approved
constraints unless the feedback clearly supports changing them. Candidate-specific
feedback can change rubric emphasis, hard filters, or both, but do not turn a vague
preference into a hard filter without evidence. Explain each meaningful change.
""".strip()

REFINE_SEARCH_USER_PROMPT = """
Original recruiter query:
{original_query}

Current filters:
{filters}

Current rubric:
{rubric}

Current ranked results:
{results}

Recruiter feedback:
{feedback}

Overall recruiter feedback:
{overall_feedback}

Produce updated filters, an updated rubric, and a short list of changes.
""".strip()
