from baires_talent_copilot.openai_analysis import (
    build_screening_prompt,
    build_system_prompt,
    preferred_language_name,
)


def test_preferred_language_name_maps_common_codes() -> None:
    assert preferred_language_name("es") == "Spanish"
    assert preferred_language_name("es-AR") == "Spanish"
    assert preferred_language_name("en") == "English"
    assert preferred_language_name("pt-BR") == "pt-BR"


def test_build_system_prompt_includes_recruiter_constraints() -> None:
    prompt = build_system_prompt("es")

    assert "human-centered screening assistant" in prompt
    assert "Do not infer protected characteristics" in prompt
    assert "Write the summary and follow-up questions in Spanish." in prompt
    assert "summary: 2 to 4 sentences" in prompt


def test_build_screening_prompt_includes_context_and_transcript() -> None:
    prompt = build_screening_prompt(
        role_title="AI Training Operations Specialist",
        role_summary="Handle screening and LLM evaluation workflows.",
        seniority="mid",
        language="es",
        must_have_skills=["Python", "LLMs"],
        nice_to_have_skills=["Prompt design"],
        messages=[
            {"speaker": "recruiter", "content": "Tell me about your work with evaluation."},
            {"speaker": "candidate", "content": "I used Python for LLM evaluation pipelines."},
        ],
    )

    assert "Role title: AI Training Operations Specialist" in prompt
    assert "Preferred output language: Spanish" in prompt
    assert "Must-have skills: Python, LLMs" in prompt
    assert "- candidate: I used Python for LLM evaluation pipelines." in prompt
    assert "Return the structured screening analysis now." in prompt
