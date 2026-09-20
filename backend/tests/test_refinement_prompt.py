from app.ai.prompts import REFINE_SEARCH_USER_PROMPT


def test_refinement_prompt_includes_overall_recruiter_feedback():
    prompt = REFINE_SEARCH_USER_PROMPT.format(
        original_query="Backend engineers",
        filters="{}",
        rubric="{}",
        results="[]",
        feedback="[]",
        overall_feedback="Only candidates based in Bangalore",
    )

    assert "Only candidates based in Bangalore" in prompt
