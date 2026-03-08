"""Authentication utilities and dependencies."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC
from datetime import timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from .db import get_session
from .models import RecruiterSessionRecord, RecruiterUserRecord
from .schemas import (
    PublicAuthConfigRead,
    RecruiterLogin,
    RecruiterRegister,
    RecruiterSessionRead,
    RecruiterUserRead,
)
from .settings import settings

security = HTTPBearer(auto_error=False)
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64


class AuthConflictError(Exception):
    """Raised when trying to create an already existing auth resource."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""


def utc_now():
    from .models import utc_now as _utc_now

    return _utc_now()


def normalize_datetime(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"scrypt${salt_b64}${digest_b64}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        _, salt_b64, digest_b64 = encoded_hash.split("$", maxsplit=2)
    except ValueError:
        return False

    salt = base64.b64decode(salt_b64.encode("ascii"))
    expected = base64.b64decode(digest_b64.encode("ascii"))
    candidate = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return hmac.compare_digest(candidate, expected)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_user_read(user: RecruiterUserRecord) -> RecruiterUserRead:
    return RecruiterUserRead.model_validate(user)


def build_auth_config() -> PublicAuthConfigRead:
    if not settings.bootstrap_demo_user:
        return PublicAuthConfigRead(demo_account_enabled=False)

    return PublicAuthConfigRead(
        demo_account_enabled=True,
        demo_email=settings.demo_user_email,
        demo_password=settings.demo_user_password,
        demo_display_name=settings.demo_user_display_name,
    )


def issue_auth_session(session: Session, user: RecruiterUserRecord) -> RecruiterSessionRead:
    raw_token = secrets.token_urlsafe(32)
    expires_at = utc_now() + timedelta(hours=settings.auth_session_ttl_hours)
    session_record = RecruiterSessionRecord(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=expires_at,
        last_seen_at=utc_now(),
    )
    user.last_login_at = utc_now()
    session.add(session_record)
    session.add(user)
    session.commit()
    session.refresh(user)
    return RecruiterSessionRead(
        access_token=raw_token,
        expires_at=expires_at,
        user=build_user_read(user),
    )


def ensure_demo_recruiter(session: Session) -> RecruiterUserRecord | None:
    if not settings.bootstrap_demo_user:
        return None

    email = normalize_email(settings.demo_user_email)
    statement = select(RecruiterUserRecord).where(RecruiterUserRecord.email == email)
    recruiter = session.exec(statement).first()
    if recruiter is not None:
        return recruiter

    recruiter = RecruiterUserRecord(
        email=email,
        display_name=settings.demo_user_display_name.strip(),
        password_hash=hash_password(settings.demo_user_password),
    )
    session.add(recruiter)
    session.commit()
    session.refresh(recruiter)
    return recruiter


def register_recruiter(session: Session, payload: RecruiterRegister) -> RecruiterSessionRead:
    email = normalize_email(payload.email)
    statement = select(RecruiterUserRecord).where(RecruiterUserRecord.email == email)
    if session.exec(statement).first() is not None:
        raise AuthConflictError("A recruiter with that email already exists")

    recruiter = RecruiterUserRecord(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
    )
    session.add(recruiter)
    session.commit()
    session.refresh(recruiter)
    return issue_auth_session(session, recruiter)


def login_recruiter(session: Session, payload: RecruiterLogin) -> RecruiterSessionRead:
    email = normalize_email(payload.email)
    statement = select(RecruiterUserRecord).where(RecruiterUserRecord.email == email)
    recruiter = session.exec(statement).first()
    if recruiter is None or not verify_password(payload.password, recruiter.password_hash):
        raise InvalidCredentialsError("Invalid email or password")
    return issue_auth_session(session, recruiter)


def resolve_session(
    session: Session,
    raw_token: str,
) -> tuple[RecruiterSessionRecord, RecruiterUserRecord]:
    statement = (
        select(RecruiterSessionRecord)
        .where(RecruiterSessionRecord.token_hash == hash_token(raw_token))
    )
    auth_session = session.exec(statement).first()
    if auth_session is None or auth_session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if normalize_datetime(auth_session.expires_at) <= utc_now():
        auth_session.revoked_at = utc_now()
        session.add(auth_session)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.get(RecruiterUserRecord, auth_session.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_session.last_seen_at = utc_now()
    session.add(auth_session)
    session.commit()
    return auth_session, user


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_current_user(
    raw_token: str = Depends(get_bearer_token),
    session: Session = Depends(get_session),
) -> RecruiterUserRecord:
    _, user = resolve_session(session, raw_token)
    return user


def logout_recruiter(session: Session, raw_token: str) -> None:
    auth_session, _ = resolve_session(session, raw_token)
    auth_session.revoked_at = utc_now()
    session.add(auth_session)
    session.commit()
