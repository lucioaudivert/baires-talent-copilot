from pathlib import Path
import sys

import pytest
from sqlmodel import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_ANALYSIS_MODEL", raising=False)

    from baires_talent_copilot.auth import ensure_demo_recruiter
    import baires_talent_copilot.db as db

    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    db.configure_engine(database_url)
    db.reset_db()
    with Session(db.engine) as session:
        ensure_demo_recruiter(session)
    yield
