"""FastAPI entrypoint for the Baires Talent Copilot v1 scaffold."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from .auth import (
    AuthConflictError,
    InvalidCredentialsError,
    build_auth_config,
    build_user_read,
    ensure_demo_recruiter,
    get_bearer_token,
    get_current_user,
    login_recruiter,
    logout_recruiter,
    register_recruiter,
)
from .db import get_session, init_db
from .schemas import (
    MessageCreate,
    MessageRead,
    PublicAuthConfigRead,
    RecruiterLogin,
    RecruiterSessionRead,
    RecruiterRegister,
    RecruiterUserRead,
    RoleProfileCreate,
    RoleProfileRead,
    ScreeningAnalysisRead,
    ScreeningAuditRead,
    ScreeningCreate,
    ScreeningDetailRead,
    ScreeningRead,
    ScreeningStatusUpdate,
)
from .services import (
    NotFoundError,
    add_message,
    bootstrap_demo,
    create_role,
    create_screening,
    generate_analysis,
    get_screening_detail,
    list_screening_audit_events,
    list_roles,
    list_screenings,
    update_screening_status,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    for session in get_session():
        ensure_demo_recruiter(session)
    yield


app = FastAPI(
    title="Baires Talent Copilot API",
    version="0.1.0",
    description="Text-first screening API for a recruiter-facing copilot.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/auth/config", response_model=PublicAuthConfigRead)
async def auth_config_endpoint() -> PublicAuthConfigRead:
    return build_auth_config()


@app.post("/auth/register", response_model=RecruiterSessionRead, status_code=status.HTTP_201_CREATED)
async def register_recruiter_endpoint(
    payload: RecruiterRegister,
    session: Annotated[Session, Depends(get_session)],
) -> RecruiterSessionRead:
    try:
        return register_recruiter(session, payload)
    except AuthConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/auth/login", response_model=RecruiterSessionRead)
async def login_recruiter_endpoint(
    payload: RecruiterLogin,
    session: Annotated[Session, Depends(get_session)],
) -> RecruiterSessionRead:
    try:
        return login_recruiter(session, payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/auth/me", response_model=RecruiterUserRead)
async def auth_me_endpoint(
    current_user=Depends(get_current_user),
) -> RecruiterUserRead:
    return build_user_read(current_user)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_recruiter_endpoint(
    raw_token: Annotated[str, Depends(get_bearer_token)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    logout_recruiter(session, raw_token)


@app.post("/roles", response_model=RoleProfileRead, status_code=status.HTTP_201_CREATED)
async def create_role_endpoint(
    payload: RoleProfileCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> RoleProfileRead:
    return create_role(session, current_user.id, payload)


@app.get("/roles", response_model=list[RoleProfileRead])
async def list_roles_endpoint(
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> list[RoleProfileRead]:
    return list_roles(session, current_user.id)


@app.post("/screenings", response_model=ScreeningRead, status_code=status.HTTP_201_CREATED)
async def create_screening_endpoint(
    payload: ScreeningCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> ScreeningRead:
    try:
        return create_screening(session, current_user.id, current_user.display_name, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/screenings", response_model=list[ScreeningRead])
async def list_screenings_endpoint(
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> list[ScreeningRead]:
    return list_screenings(session, current_user.id)


@app.get("/screenings/{screening_id}", response_model=ScreeningDetailRead)
async def get_screening_endpoint(
    screening_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> ScreeningDetailRead:
    try:
        return get_screening_detail(session, current_user.id, screening_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/screenings/{screening_id}/audit", response_model=list[ScreeningAuditRead])
async def get_screening_audit_endpoint(
    screening_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> list[ScreeningAuditRead]:
    try:
        return list_screening_audit_events(session, current_user.id, screening_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/screenings/{screening_id}/status", response_model=ScreeningRead)
async def update_screening_status_endpoint(
    screening_id: int,
    payload: ScreeningStatusUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> ScreeningRead:
    try:
        return update_screening_status(
            session,
            current_user.id,
            current_user.display_name,
            screening_id,
            payload,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/screenings/{screening_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_message_endpoint(
    screening_id: int,
    payload: MessageCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> MessageRead:
    try:
        return add_message(
            session,
            current_user.id,
            current_user.display_name,
            screening_id,
            payload,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/screenings/{screening_id}/analysis",
    response_model=ScreeningAnalysisRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_analysis_endpoint(
    screening_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> ScreeningAnalysisRead:
    try:
        return generate_analysis(session, current_user.id, screening_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/demo/bootstrap",
    response_model=ScreeningDetailRead,
    status_code=status.HTTP_201_CREATED,
)
async def bootstrap_demo_endpoint(
    session: Annotated[Session, Depends(get_session)],
    current_user=Depends(get_current_user),
) -> ScreeningDetailRead:
    return bootstrap_demo(session, current_user.id, current_user.display_name)
