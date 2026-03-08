"""API schemas for the text-first screening workflow."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ScreeningStatus(StrEnum):
    draft = "draft"
    in_progress = "in_progress"
    review_ready = "review_ready"


class SpeakerRole(StrEnum):
    recruiter = "recruiter"
    candidate = "candidate"
    assistant = "assistant"


class AnalysisSource(StrEnum):
    heuristic = "heuristic"
    openai = "openai"


class ScreeningAuditEventType(StrEnum):
    screening_created = "screening_created"
    message_added = "message_added"
    analysis_generated = "analysis_generated"
    analysis_cleared = "analysis_cleared"
    status_changed = "status_changed"
    demo_bootstrapped = "demo_bootstrapped"


class ScreeningAuditActorType(StrEnum):
    recruiter = "recruiter"
    assistant = "assistant"
    system = "system"


class RecruiterRegister(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class RecruiterLogin(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class RecruiterUserRead(BaseModel):
    id: int
    email: str
    display_name: str
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RecruiterSessionRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: RecruiterUserRead


class PublicAuthConfigRead(BaseModel):
    demo_account_enabled: bool
    demo_email: str | None = None
    demo_password: str | None = None
    demo_display_name: str | None = None


class RoleProfileCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    seniority: str = Field(min_length=1, max_length=50)
    language: str = Field(default="es", min_length=2, max_length=10)
    summary: str = Field(min_length=1, max_length=500)
    must_have_skills: list[str] = Field(default_factory=list, max_length=12)
    nice_to_have_skills: list[str] = Field(default_factory=list, max_length=12)


class RoleProfileRead(RoleProfileCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScreeningCreate(BaseModel):
    role_id: int = Field(gt=0)
    candidate_name: str = Field(min_length=1, max_length=120)
    candidate_email: str | None = Field(default=None, max_length=200)
    intro_notes: str | None = Field(default=None, max_length=500)


class ScreeningRead(BaseModel):
    id: int
    role_id: int
    candidate_name: str
    candidate_email: str | None
    intro_notes: str | None
    status: ScreeningStatus
    message_count: int
    latest_summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScreeningStatusUpdate(BaseModel):
    status: ScreeningStatus


class MessageCreate(BaseModel):
    speaker: SpeakerRole
    content: str = Field(min_length=1, max_length=2000)


class MessageRead(MessageCreate):
    id: int
    screening_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScreeningAuditRead(BaseModel):
    id: int
    screening_id: int
    event_type: ScreeningAuditEventType
    actor_type: ScreeningAuditActorType
    actor_label: str
    summary: str
    payload: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScreeningAnalysisPayload(BaseModel):
    summary: str
    matched_skills: list[str]
    missing_signals: list[str]
    follow_up_questions: list[str]
    recommended_status: ScreeningStatus
    confidence_score: float = Field(ge=0, le=1)


class ScreeningAnalysisRead(ScreeningAnalysisPayload):
    analysis_source: AnalysisSource
    generated_at: datetime


class ScreeningDetailRead(ScreeningRead):
    role: RoleProfileRead
    messages: list[MessageRead]
    latest_analysis: ScreeningAnalysisRead | None = None
    audit_events: list[ScreeningAuditRead] = Field(default_factory=list)
