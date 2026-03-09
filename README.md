# Baires Talent Copilot

[![CI](https://github.com/lucioaudivert/baires-talent-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/lucioaudivert/baires-talent-copilot/actions/workflows/ci.yml)

Text-first screening copilot for recruiters and training teams.

## 60-Second Overview

Early-stage screening is often noisy, hard to compare, and hard to audit.

Baires Talent Copilot solves that with a focused workflow:
- define a role profile with required signals
- run a structured screening chat
- generate an explainable summary and follow-up questions
- keep an audit trail of recruiter and system actions
- keep final decisions human-led (`review_ready` is only a recommendation)

This project is intentionally narrow by design. It optimizes for clarity, traceability, and product execution over feature sprawl.

## Why This Is a Strong Flagship Project

- End-to-end product slice: auth, API, persistence, UI, and tests
- AI with guardrails: structured outputs + conservative fallback
- Real workflow constraints: private recruiter-scoped data and auditable events
- Practical engineering: works fully without paid AI APIs

## Product Scope (v1)

- recruiter auth (register, login, logout, session restore)
- role profile creation (must-have and nice-to-have skills)
- screening pipeline board with search, filters, and drag-and-drop status updates
- conversation timeline per screening
- analysis generation with:
  - `openai` mode when `OPENAI_API_KEY` is configured
  - `heuristic` mode when no key is available
- full audit timeline (`screening_created`, `message_added`, `analysis_generated`, `status_changed`, etc.)
- seeded demo workflow (`POST /demo/bootstrap`) for fast portfolio review

## Quick Demo (Local, 2 Minutes)

```bash
cd baires-talent-copilot
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn baires_talent_copilot.main:app --reload
```

Open:
- App UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

Demo credentials (enabled by default):
- Email: `recruiter@baires.demo`
- Password: `TalentDemo2026!`

After login, click `Load Demo Workflow` to populate a full recruiter flow instantly.

## Tech Stack

- FastAPI
- SQLModel + SQLAlchemy
- SQLite by default (`sqlite:///./baires_talent_copilot.db`)
- Postgres-ready via `COPILOT_DATABASE_URL`
- OpenAI Python SDK (`responses.parse`) for structured analysis
- Plain HTML/CSS/JS frontend served by FastAPI
- Pytest test suite

## Key Engineering Decisions

1. AI is optional, not a hard dependency
- If `OPENAI_API_KEY` is missing or fails, analysis falls back to deterministic heuristics.

2. Structured analysis output
- Both AI and heuristic paths return the same `ScreeningAnalysisPayload` contract.

3. Human-in-the-loop by default
- Assistant output recommends status; recruiter can override and changes are audited.

4. Data isolation per recruiter
- Roles, screenings, and seeded demo data are scoped by authenticated user.

5. Traceability as a first-class concern
- Every meaningful action is persisted in audit events.

6. Analysis invalidation on new evidence
- Adding a message clears stale analysis and records `analysis_cleared`.

## Configuration

Copy `.env.example` or export variables directly:

```bash
COPILOT_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/baires_talent_copilot
COPILOT_AUTH_SESSION_TTL_HOURS=168
COPILOT_BOOTSTRAP_DEMO_USER=true
COPILOT_DEMO_USER_EMAIL=recruiter@baires.demo
COPILOT_DEMO_USER_PASSWORD=TalentDemo2026!
COPILOT_DEMO_USER_DISPLAY_NAME=Demo Recruiter
OPENAI_API_KEY=
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
```

## API Surface

Auth:
- `GET /auth/config`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

Workflow:
- `POST /roles`
- `GET /roles`
- `POST /screenings`
- `GET /screenings`
- `GET /screenings/{screening_id}`
- `PATCH /screenings/{screening_id}/status`
- `POST /screenings/{screening_id}/messages`
- `POST /screenings/{screening_id}/analysis`
- `GET /screenings/{screening_id}/audit`
- `POST /demo/bootstrap`

Utility:
- `GET /health`

## Testing

```bash
pytest
```

Current tests cover:
- auth flow (register/login/logout/session)
- protected routes
- recruiter data isolation
- screening lifecycle and audit events
- analysis generation behavior
- prompt-building logic for OpenAI mode

## Repository Layout

```text
src/baires_talent_copilot/
  main.py              # FastAPI app and routes
  auth.py              # auth, token session handling, password hashing
  services.py          # core screening workflow logic
  openai_analysis.py   # OpenAI structured analysis path
  db.py                # engine/session setup
  models.py            # SQLModel records
  schemas.py           # Pydantic API contracts
  static/              # recruiter-facing UI
tests/
  test_api.py
  test_openai_analysis.py
```

## Next Milestones

- add CI workflow (tests + lint on push/PR)
- add role calibration/evaluation dataset for regression checks
- add richer analytics around false positives and missing signals
- add async transcription as a later multimodal step
