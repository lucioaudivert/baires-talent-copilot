"""Persistence-backed services for Baires Talent Copilot."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from .models import (
    RecruiterUserRecord,
    RoleProfileRecord,
    ScreeningAuditRecord,
    ScreeningMessageRecord,
    ScreeningRecord,
)
from .openai_analysis import generate_openai_analysis
from .schemas import (
    AnalysisSource,
    MessageCreate,
    MessageRead,
    RoleProfileCreate,
    RoleProfileRead,
    ScreeningAnalysisPayload,
    ScreeningAnalysisRead,
    ScreeningAuditActorType,
    ScreeningAuditEventType,
    ScreeningAuditRead,
    ScreeningCreate,
    ScreeningDetailRead,
    ScreeningRead,
    ScreeningStatusUpdate,
    ScreeningStatus,
    SpeakerRole,
)


class NotFoundError(Exception):
    """Raised when an entity cannot be found."""


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_skills(values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []

    for value in values:
        cleaned = " ".join(value.split()).strip()
        if not cleaned:
            continue

        key = cleaned.casefold()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(cleaned)

    return normalized


def skill_signals(skill: str) -> list[str]:
    normalized = " ".join(skill.split()).strip().casefold()
    if not normalized:
        return []

    signals = [normalized]
    if normalized.endswith("s") and len(normalized) > 3:
        signals.append(normalized[:-1])

    return signals


def build_analysis_read(
    *,
    payload: ScreeningAnalysisPayload,
    analysis_source: AnalysisSource,
) -> ScreeningAnalysisRead:
    return ScreeningAnalysisRead(
        summary=payload.summary,
        matched_skills=payload.matched_skills,
        missing_signals=payload.missing_signals,
        follow_up_questions=payload.follow_up_questions,
        recommended_status=payload.recommended_status,
        confidence_score=payload.confidence_score,
        analysis_source=analysis_source,
        generated_at=utc_now(),
    )


def load_analysis(payload: dict | None) -> ScreeningAnalysisRead | None:
    if payload is None:
        return None
    return ScreeningAnalysisRead.model_validate(payload)


def build_role_read(record: RoleProfileRecord) -> RoleProfileRead:
    return RoleProfileRead.model_validate(record)


def build_message_read(record: ScreeningMessageRecord) -> MessageRead:
    return MessageRead.model_validate(record)


def build_audit_read(record: ScreeningAuditRecord) -> ScreeningAuditRead:
    return ScreeningAuditRead.model_validate(record)


def build_screening_read(record: ScreeningRecord) -> ScreeningRead:
    latest_analysis = load_analysis(record.latest_analysis_payload)
    latest_summary = latest_analysis.summary if latest_analysis else None
    message_count = len(record.messages)

    return ScreeningRead(
        id=record.id,
        role_id=record.role_id,
        candidate_name=record.candidate_name,
        candidate_email=record.candidate_email,
        intro_notes=record.intro_notes,
        status=record.status,
        message_count=message_count,
        latest_summary=latest_summary,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def screening_query():
    return select(ScreeningRecord).options(
        selectinload(ScreeningRecord.role),
        selectinload(ScreeningRecord.messages),
        selectinload(ScreeningRecord.audit_events),
    )


def create_audit_event(
    *,
    screening_id: int,
    event_type: ScreeningAuditEventType,
    actor_type: ScreeningAuditActorType,
    actor_label: str,
    summary: str,
    payload: dict | None = None,
) -> ScreeningAuditRecord:
    return ScreeningAuditRecord(
        screening_id=screening_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_label=actor_label,
        summary=summary,
        payload=payload,
    )


def get_role_record(
    session: Session,
    owner_user_id: int,
    role_id: int,
) -> RoleProfileRecord:
    statement = select(RoleProfileRecord).where(
        RoleProfileRecord.id == role_id,
        RoleProfileRecord.owner_user_id == owner_user_id,
    )
    role = session.exec(statement).first()
    if role is None:
        raise NotFoundError("Role not found")
    return role


def get_screening_record(
    session: Session,
    owner_user_id: int,
    screening_id: int,
) -> ScreeningRecord:
    statement = screening_query().where(
        ScreeningRecord.id == screening_id,
        ScreeningRecord.owner_user_id == owner_user_id,
    )
    screening = session.exec(statement).one_or_none()
    if screening is None:
        raise NotFoundError("Screening not found")
    return screening


def create_role(
    session: Session,
    owner_user_id: int,
    payload: RoleProfileCreate,
) -> RoleProfileRead:
    role = RoleProfileRecord(
        owner_user_id=owner_user_id,
        title=payload.title.strip(),
        seniority=payload.seniority.strip(),
        language=payload.language.strip(),
        summary=payload.summary.strip(),
        must_have_skills=normalize_skills(payload.must_have_skills),
        nice_to_have_skills=normalize_skills(payload.nice_to_have_skills),
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    return build_role_read(role)


def list_roles(session: Session, owner_user_id: int) -> list[RoleProfileRead]:
    statement = (
        select(RoleProfileRecord)
        .where(RoleProfileRecord.owner_user_id == owner_user_id)
        .order_by(RoleProfileRecord.created_at.desc())
    )
    return [build_role_read(role) for role in session.exec(statement)]


def create_screening(
    session: Session,
    owner_user_id: int,
    actor_label: str,
    payload: ScreeningCreate,
) -> ScreeningRead:
    role = get_role_record(session, owner_user_id, payload.role_id)
    screening = ScreeningRecord(
        owner_user_id=owner_user_id,
        role_id=payload.role_id,
        candidate_name=payload.candidate_name.strip(),
        candidate_email=payload.candidate_email.strip() if payload.candidate_email else None,
        intro_notes=payload.intro_notes.strip() if payload.intro_notes else None,
        status=ScreeningStatus.draft,
    )
    audit_event = create_audit_event(
        screening_id=0,
        event_type=ScreeningAuditEventType.screening_created,
        actor_type=ScreeningAuditActorType.recruiter,
        actor_label=actor_label,
        summary=f"Created screening for {payload.candidate_name.strip()}",
        payload={
            "candidate_name": payload.candidate_name.strip(),
            "role_title": role.title,
            "intro_notes": payload.intro_notes.strip() if payload.intro_notes else None,
        },
    )
    session.add(screening)
    session.commit()
    session.refresh(screening)
    audit_event.screening_id = screening.id
    session.add(audit_event)
    session.commit()
    screening = get_screening_record(session, owner_user_id, screening.id)
    return build_screening_read(screening)


def list_screenings(session: Session, owner_user_id: int) -> list[ScreeningRead]:
    statement = (
        screening_query()
        .where(ScreeningRecord.owner_user_id == owner_user_id)
        .order_by(ScreeningRecord.updated_at.desc())
    )
    return [build_screening_read(screening) for screening in session.exec(statement)]


def get_screening_detail(
    session: Session,
    owner_user_id: int,
    screening_id: int,
) -> ScreeningDetailRead:
    screening = get_screening_record(session, owner_user_id, screening_id)
    role = screening.role or get_role_record(session, owner_user_id, screening.role_id)
    summary = build_screening_read(screening)

    return ScreeningDetailRead(
        **summary.model_dump(),
        role=build_role_read(role),
        messages=[build_message_read(message) for message in screening.messages],
        latest_analysis=load_analysis(screening.latest_analysis_payload),
        audit_events=[build_audit_read(event) for event in screening.audit_events],
    )


def list_screening_audit_events(
    session: Session,
    owner_user_id: int,
    screening_id: int,
) -> list[ScreeningAuditRead]:
    screening = get_screening_record(session, owner_user_id, screening_id)
    return [build_audit_read(event) for event in screening.audit_events]


def add_message(
    session: Session,
    owner_user_id: int,
    actor_label: str,
    screening_id: int,
    payload: MessageCreate,
) -> MessageRead:
    screening = get_screening_record(session, owner_user_id, screening_id)
    had_analysis = screening.latest_analysis_payload is not None
    message = ScreeningMessageRecord(
        screening_id=screening_id,
        speaker=payload.speaker,
        content=payload.content.strip(),
    )

    screening.updated_at = utc_now()
    screening.status = ScreeningStatus.in_progress
    screening.latest_analysis_payload = None
    audit_event = create_audit_event(
        screening_id=screening_id,
        event_type=ScreeningAuditEventType.message_added,
        actor_type=ScreeningAuditActorType.recruiter,
        actor_label=actor_label,
        summary=f"Added {payload.speaker.value} message",
        payload={
            "speaker": payload.speaker.value,
            "preview": payload.content.strip()[:160],
        },
    )

    session.add(message)
    session.add(screening)
    session.add(audit_event)
    if had_analysis:
        session.add(
            create_audit_event(
                screening_id=screening_id,
                event_type=ScreeningAuditEventType.analysis_cleared,
                actor_type=ScreeningAuditActorType.system,
                actor_label="System",
                summary="Cleared previous analysis after a new message was added",
                payload={"reason": "new_message"},
            )
        )
    session.commit()
    session.refresh(message)
    return build_message_read(message)


def update_screening_status(
    session: Session,
    owner_user_id: int,
    actor_label: str,
    screening_id: int,
    payload: ScreeningStatusUpdate,
) -> ScreeningRead:
    screening = get_screening_record(session, owner_user_id, screening_id)
    if screening.status == payload.status:
        return build_screening_read(screening)

    previous_status = screening.status
    screening.status = payload.status
    screening.updated_at = utc_now()

    session.add(screening)
    session.add(
        create_audit_event(
            screening_id=screening_id,
            event_type=ScreeningAuditEventType.status_changed,
            actor_type=ScreeningAuditActorType.recruiter,
            actor_label=actor_label,
            summary=(
                f"Moved screening from {previous_status.value} to {payload.status.value}"
            ),
            payload={
                "from_status": previous_status.value,
                "to_status": payload.status.value,
            },
        )
    )
    session.commit()
    screening = get_screening_record(session, owner_user_id, screening_id)
    return build_screening_read(screening)


def build_heuristic_analysis(
    screening: ScreeningRecord,
    role: RoleProfileRecord,
) -> ScreeningAnalysisPayload:
    candidate_messages = [
        message.content for message in screening.messages if message.speaker == SpeakerRole.candidate
    ]
    combined_text = " ".join(candidate_messages).casefold()
    message_count = len(candidate_messages)

    matched_skills = [
        skill
        for skill in role.must_have_skills
        if any(signal in combined_text for signal in skill_signals(skill))
    ]
    missing_signals = [
        skill
        for skill in role.must_have_skills
        if not any(signal in combined_text for signal in skill_signals(skill))
    ]

    follow_up_questions: list[str] = []
    if missing_signals:
        follow_up_questions.append(
            f"Ask for a concrete example using {missing_signals[0]} in production."
        )
    if "team" not in combined_text and "stakeholder" not in combined_text:
        follow_up_questions.append("Ask how the candidate collaborates with teams or stakeholders.")
    if "measure" not in combined_text and "metric" not in combined_text:
        follow_up_questions.append("Ask how the candidate measures quality or impact.")
    if not follow_up_questions:
        follow_up_questions.append("Ask for a recent project tradeoff and the final decision.")

    ratio = len(matched_skills) / len(role.must_have_skills) if role.must_have_skills else 1.0
    confidence_score = min(0.55 + (ratio * 0.35) + min(message_count, 4) * 0.02, 0.95)

    recommended_status = (
        ScreeningStatus.review_ready
        if message_count >= 2 and ratio >= 0.5
        else ScreeningStatus.in_progress
    )

    summary = (
        f"{screening.candidate_name} completed {message_count} candidate messages for "
        f"{role.title}. Matched {len(matched_skills)} of {len(role.must_have_skills)} "
        "required skill signals in the conversation."
    )

    return ScreeningAnalysisPayload(
        summary=summary,
        matched_skills=matched_skills,
        missing_signals=missing_signals,
        follow_up_questions=follow_up_questions,
        recommended_status=recommended_status,
        confidence_score=round(confidence_score, 2),
    )


def bootstrap_demo(
    session: Session,
    owner_user_id: int,
    actor_label: str,
) -> ScreeningDetailRead:
    """Create or reuse a portfolio-ready demo workflow."""

    role_statement = select(RoleProfileRecord).where(
        RoleProfileRecord.owner_user_id == owner_user_id,
        RoleProfileRecord.title == "AI Training Operations Specialist",
    )
    role = session.exec(role_statement).first()
    if role is None:
        role = RoleProfileRecord(
            owner_user_id=owner_user_id,
            title="AI Training Operations Specialist",
            seniority="mid",
            language="es",
            summary=(
                "Profile focused on LLM operations, evaluator workflows, prompt quality, "
                "and communication with client teams."
            ),
            must_have_skills=["Python", "LLMs", "Evaluation", "Stakeholders"],
            nice_to_have_skills=["FastAPI", "Education", "Prompt design"],
        )
        session.add(role)
        session.commit()
        session.refresh(role)

    screening_statement = screening_query().where(
        ScreeningRecord.owner_user_id == owner_user_id,
        ScreeningRecord.role_id == role.id,
        ScreeningRecord.candidate_email == "julieta@example.com",
    )
    screening = session.exec(screening_statement).first()
    if screening is None:
        screening = ScreeningRecord(
            owner_user_id=owner_user_id,
            role_id=role.id,
            candidate_name="Julieta Acosta",
            candidate_email="julieta@example.com",
            intro_notes="Strong operations profile with a psychology background.",
        )
        session.add(screening)
        session.commit()
        session.refresh(screening)
        session.add(
            create_audit_event(
                screening_id=screening.id,
                event_type=ScreeningAuditEventType.screening_created,
                actor_type=ScreeningAuditActorType.recruiter,
                actor_label=actor_label,
                summary=f"Created screening for {screening.candidate_name}",
                payload={
                    "candidate_name": screening.candidate_name,
                    "role_title": role.title,
                    "intro_notes": screening.intro_notes,
                },
            )
        )
        session.commit()
        screening = get_screening_record(session, owner_user_id, screening.id)

    if not screening.messages:
        add_message(
            session,
            owner_user_id,
            actor_label,
            screening.id,
            MessageCreate(
                speaker=SpeakerRole.recruiter,
                content="Tell me about a project where you worked with LLM quality or evaluation.",
            ),
        )
        add_message(
            session,
            owner_user_id,
            actor_label,
            screening.id,
            MessageCreate(
                speaker=SpeakerRole.candidate,
                content=(
                    "I worked on LLM evaluation pipelines for customer support and training data. "
                    "I used Python to prepare datasets, review outputs, and improve prompt quality."
                ),
            ),
        )
        add_message(
            session,
            owner_user_id,
            actor_label,
            screening.id,
            MessageCreate(
                speaker=SpeakerRole.candidate,
                content=(
                    "I usually coordinate with stakeholders from operations and product, and I define "
                    "simple metrics to measure response quality, consistency, and escalation accuracy."
                ),
            ),
        )

    if load_analysis(screening.latest_analysis_payload) is None:
        generate_analysis(session, owner_user_id, screening.id)
        session.add(
            create_audit_event(
                screening_id=screening.id,
                event_type=ScreeningAuditEventType.demo_bootstrapped,
                actor_type=ScreeningAuditActorType.system,
                actor_label="Demo bootstrap",
                summary="Loaded the seeded portfolio workflow",
                payload={"candidate_name": screening.candidate_name},
            )
        )
        session.commit()

    return get_screening_detail(session, owner_user_id, screening.id)


def generate_analysis(
    session: Session,
    owner_user_id: int,
    screening_id: int,
) -> ScreeningAnalysisRead:
    screening = get_screening_record(session, owner_user_id, screening_id)
    role = screening.role or get_role_record(session, owner_user_id, screening.role_id)

    openai_payload = generate_openai_analysis(
        role_title=role.title,
        role_summary=role.summary,
        seniority=role.seniority,
        language=role.language,
        must_have_skills=role.must_have_skills,
        nice_to_have_skills=role.nice_to_have_skills,
        messages=[
            {"speaker": message.speaker.value, "content": message.content}
            for message in screening.messages
        ],
    )

    if openai_payload is not None:
        analysis = build_analysis_read(
            payload=openai_payload,
            analysis_source=AnalysisSource.openai,
        )
    else:
        analysis = build_analysis_read(
            payload=build_heuristic_analysis(screening, role),
            analysis_source=AnalysisSource.heuristic,
        )

    screening.latest_analysis_payload = analysis.model_dump(mode="json")
    screening.status = analysis.recommended_status
    screening.updated_at = utc_now()
    session.add(screening)
    session.add(
        create_audit_event(
            screening_id=screening.id,
            event_type=ScreeningAuditEventType.analysis_generated,
            actor_type=ScreeningAuditActorType.assistant,
            actor_label=analysis.analysis_source.value,
            summary=f"Generated {analysis.analysis_source.value} analysis",
            payload={
                "analysis_source": analysis.analysis_source.value,
                "recommended_status": analysis.recommended_status.value,
                "confidence_score": analysis.confidence_score,
            },
        )
    )
    session.commit()
    return analysis
