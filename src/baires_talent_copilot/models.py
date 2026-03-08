"""Persistence models for Baires Talent Copilot."""

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import Column, JSON, String
from sqlmodel import Field, Relationship, SQLModel

from .schemas import ScreeningAuditActorType, ScreeningAuditEventType, ScreeningStatus, SpeakerRole


def utc_now() -> datetime:
    return datetime.now(UTC)


class RoleProfileRecord(SQLModel, table=True):
    __tablename__ = "role_profiles"

    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: int = Field(foreign_key="recruiter_users.id", index=True)
    title: str = Field(max_length=120, index=True)
    seniority: str = Field(max_length=50, index=True)
    language: str = Field(default="es", max_length=10)
    summary: str = Field(max_length=500)
    must_have_skills: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    nice_to_have_skills: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)

    owner: Optional["RecruiterUserRecord"] = Relationship(back_populates="role_profiles")
    screenings: list["ScreeningRecord"] = Relationship(back_populates="role")


class ScreeningRecord(SQLModel, table=True):
    __tablename__ = "screenings"

    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: int = Field(foreign_key="recruiter_users.id", index=True)
    role_id: int = Field(foreign_key="role_profiles.id", index=True)
    candidate_name: str = Field(max_length=120, index=True)
    candidate_email: str | None = Field(default=None, max_length=200, index=True)
    intro_notes: str | None = Field(default=None, max_length=500)
    status: ScreeningStatus = Field(default=ScreeningStatus.draft, index=True)
    latest_analysis_payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)

    owner: Optional["RecruiterUserRecord"] = Relationship(back_populates="screenings")
    role: Optional[RoleProfileRecord] = Relationship(back_populates="screenings")
    messages: list["ScreeningMessageRecord"] = Relationship(
        back_populates="screening",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ScreeningMessageRecord.created_at",
        },
    )
    audit_events: list["ScreeningAuditRecord"] = Relationship(
        back_populates="screening",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ScreeningAuditRecord.created_at",
        },
    )


class ScreeningMessageRecord(SQLModel, table=True):
    __tablename__ = "screening_messages"

    id: int | None = Field(default=None, primary_key=True)
    screening_id: int = Field(foreign_key="screenings.id", index=True)
    speaker: SpeakerRole = Field(index=True)
    content: str = Field(max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)

    screening: Optional[ScreeningRecord] = Relationship(back_populates="messages")


class ScreeningAuditRecord(SQLModel, table=True):
    __tablename__ = "screening_audit_events"

    id: int | None = Field(default=None, primary_key=True)
    screening_id: int = Field(foreign_key="screenings.id", index=True)
    event_type: ScreeningAuditEventType = Field(index=True)
    actor_type: ScreeningAuditActorType = Field(index=True)
    actor_label: str = Field(max_length=120)
    summary: str = Field(max_length=240)
    payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)

    screening: Optional[ScreeningRecord] = Relationship(back_populates="audit_events")


class RecruiterUserRecord(SQLModel, table=True):
    __tablename__ = "recruiter_users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(
        sa_column=Column(String(320), unique=True, nullable=False, index=True),
    )
    display_name: str = Field(max_length=120)
    password_hash: str = Field(max_length=512)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    last_login_at: datetime | None = Field(default=None, nullable=True)

    role_profiles: list[RoleProfileRecord] = Relationship(back_populates="owner")
    screenings: list[ScreeningRecord] = Relationship(back_populates="owner")
    auth_sessions: list["RecruiterSessionRecord"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class RecruiterSessionRecord(SQLModel, table=True):
    __tablename__ = "recruiter_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="recruiter_users.id", index=True)
    token_hash: str = Field(
        sa_column=Column(String(128), unique=True, nullable=False, index=True),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    expires_at: datetime = Field(nullable=False, index=True)
    revoked_at: datetime | None = Field(default=None, nullable=True, index=True)
    last_seen_at: datetime | None = Field(default=None, nullable=True)

    user: Optional[RecruiterUserRecord] = Relationship(back_populates="auth_sessions")
