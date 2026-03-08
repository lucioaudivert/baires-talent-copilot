"""Database engine and session management."""

from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401
from .settings import settings


def build_engine(database_url: str | None = None):
    url = database_url or settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=False, connect_args=connect_args)


engine = build_engine()


def configure_engine(database_url: str) -> None:
    global engine
    engine.dispose()
    engine = build_engine(database_url)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def reset_db() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
