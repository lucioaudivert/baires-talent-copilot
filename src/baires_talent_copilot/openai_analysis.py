"""OpenAI-backed screening analysis with structured outputs."""

from __future__ import annotations

import logging
import os

from .schemas import ScreeningAnalysisPayload

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_ANALYSIS_MODEL = "gpt-4.1-mini"


def preferred_language_name(language: str) -> str:
    normalized = language.strip().casefold()
    if normalized.startswith("es"):
        return "Spanish"
    if normalized.startswith("en"):
        return "English"
    return language or "the requested language"


def build_system_prompt(language: str) -> str:
    preferred_language = preferred_language_name(language)
    return f"""
You are Baires Talent Copilot, a human-centered screening assistant for recruiters and training teams.

Your job is to produce a conservative screening analysis for human review, not to make final hiring decisions.

Rules:
- Focus only on job-relevant evidence from the transcript.
- Do not infer protected characteristics or personality traits that are not explicitly supported.
- Count a skill as matched only when there is direct evidence in the conversation.
- Use missing_signals only for must-have skills or critical work signals that still need validation.
- Keep the tone practical, recruiter-facing, and concise.
- Write the summary and follow-up questions in {preferred_language}.
- Recommended status should be review_ready only when there is enough evidence to justify human review.
- Confidence score should reflect evidence quality, specificity, and completeness, not optimism.

Output guidance:
- summary: 2 to 4 sentences, mention relevant evidence, likely fit, and any caution.
- matched_skills: only skills clearly supported by the transcript.
- missing_signals: only skills or signals that are still not evidenced.
- follow_up_questions: 2 to 4 concrete questions that reduce uncertainty.
""".strip()


def build_screening_prompt(
    *,
    role_title: str,
    role_summary: str,
    seniority: str,
    language: str,
    must_have_skills: list[str],
    nice_to_have_skills: list[str],
    messages: list[dict[str, str]],
) -> str:
    transcript = "\n".join(
        f"- {message['speaker']}: {message['content']}" for message in messages
    )
    must_have = ", ".join(must_have_skills) if must_have_skills else "None"
    nice_to_have = ", ".join(nice_to_have_skills) if nice_to_have_skills else "None"
    preferred_language = preferred_language_name(language)

    return f"""
Screening context
- Role title: {role_title}
- Seniority: {seniority}
- Preferred output language: {preferred_language}
- Role summary: {role_summary}
- Must-have skills: {must_have}
- Nice-to-have skills: {nice_to_have}

Instructions
- Evaluate whether the candidate shows evidence for the must-have skills.
- Consider communication, stakeholder handling, clarity, and operational judgment only when the transcript supports it.
- If evidence is weak or missing, keep the recommendation conservative.
- Avoid generic praise.

Conversation transcript:
{transcript}

Return the structured screening analysis now.
""".strip()


def generate_openai_analysis(
    *,
    role_title: str,
    role_summary: str,
    seniority: str,
    language: str,
    must_have_skills: list[str],
    nice_to_have_skills: list[str],
    messages: list[dict[str, str]],
) -> ScreeningAnalysisPayload | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("OpenAI package is not installed; using heuristic analysis instead.")
        return None

    model = os.getenv("OPENAI_ANALYSIS_MODEL", DEFAULT_OPENAI_ANALYSIS_MODEL)
    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.parse(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": build_system_prompt(language),
                },
                {
                    "role": "user",
                    "content": build_screening_prompt(
                        role_title=role_title,
                        role_summary=role_summary,
                        seniority=seniority,
                        language=language,
                        must_have_skills=must_have_skills,
                        nice_to_have_skills=nice_to_have_skills,
                        messages=messages,
                    ),
                },
            ],
            text_format=ScreeningAnalysisPayload,
        )
    except Exception as exc:
        logger.warning("OpenAI analysis failed; using heuristic fallback. %s", exc)
        return None

    return response.output_parsed
