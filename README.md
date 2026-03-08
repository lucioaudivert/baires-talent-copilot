# Baires Talent Copilot

Text-first screening copilot for recruiters and training teams.

This v1 keeps the scope intentionally narrow. It focuses on structured intake, explainable summaries, and recruiter-friendly follow-up suggestions without adding voice, realtime streaming, or agent orchestration yet.

## Why This Project

This project is the flagship piece for the portfolio. It combines:
- conversational UX
- applied AI workflows
- recruiting and screening operations
- psychology-informed product thinking

## v1 Scope

- create role profiles
- open candidate screenings
- review screenings in a board view with search, filters, and drag-and-drop status changes
- add chat messages to a screening
- generate a structured analysis
- keep an auditable timeline of recruiter and system actions
- mark the screening as ready for human review

## API Surface

- `GET /health`
- `GET /auth/config`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`
- `POST /roles`
- `GET /roles`
- `POST /screenings`
- `GET /screenings`
- `GET /screenings/{screening_id}`
- `PATCH /screenings/{screening_id}/status`
- `GET /screenings/{screening_id}/audit`
- `POST /screenings/{screening_id}/messages`
- `POST /screenings/{screening_id}/analysis`

## Tech Direction

- FastAPI for the backend API
- persistent storage through SQLModel
- SQLite by default for quick local demos
- Postgres-ready through `COPILOT_DATABASE_URL`
- heuristic fallback when no API key is configured
- OpenAI structured extraction when `OPENAI_API_KEY` is available
- recruiter auth with token sessions and private recruiter-scoped data

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn baires_talent_copilot.main:app --reload
```

The recruiter-facing demo UI and API will be available at `http://localhost:8000`.

By default the app writes to a local SQLite file. To use Postgres instead:

```bash
export COPILOT_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/baires_talent_copilot"
```

The app also bootstraps a portfolio demo recruiter by default:

```bash
export COPILOT_BOOTSTRAP_DEMO_USER=true
export COPILOT_DEMO_USER_EMAIL="recruiter@baires.demo"
export COPILOT_DEMO_USER_PASSWORD="TalentDemo2026!"
export COPILOT_DEMO_USER_DISPLAY_NAME="Demo Recruiter"
```

## Optional OpenAI Setup

If you want the screening analysis to use OpenAI instead of local rules:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_ANALYSIS_MODEL="gpt-4.1-mini"
```

Without those variables, the project still works and falls back to heuristic analysis.

## Persistence Notes

- role profiles, screenings, messages, and the latest analysis are now stored in the database
- screening audit events are stored in the database for recruiter-facing traceability
- manual status moves from the pipeline board are persisted and audited
- auth sessions are stored in the database and can be revoked by logging out
- each recruiter only sees their own roles, screenings, and seeded demo data
- clicking `Load Demo Workflow` is idempotent and reuses the same seeded demo screening
- adding a new message clears the previous analysis so the reviewer can regenerate it

## Run Tests

```bash
pytest
```

## Example Flow

Open the browser and sign in:

```bash
http://localhost:8000
```

You can either register a recruiter account or use the default portfolio demo account:

```text
Email: recruiter@baires.demo
Password: TalentDemo2026!
```

Or bootstrap a ready-made workflow after logging in:

```bash
curl -X POST http://localhost:8000/demo/bootstrap
```

Register a recruiter:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Lucio Recruiter",
    "email": "lucio@example.com",
    "password": "Talent1234!"
  }'
```

Then create a role with the returned bearer token:

```bash
curl -X POST http://localhost:8000/roles \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI Recruiter Assistant",
    "seniority": "mid",
    "language": "es",
    "summary": "Screening role for candidate operations",
    "must_have_skills": ["Python", "FastAPI", "LLMs"],
    "nice_to_have_skills": ["Postgres", "Prompt design"]
  }'
```

Open a screening:

```bash
curl -X POST http://localhost:8000/screenings \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role_id": 1,
    "candidate_name": "Ana Lopez",
    "candidate_email": "ana@example.com",
    "intro_notes": "Candidate came from a referral."
  }'
```

Add candidate messages:

```bash
curl -X POST http://localhost:8000/screenings/1/messages \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "speaker": "candidate",
    "content": "I have worked with Python, FastAPI, and LLM evaluation flows."
  }'
```

Generate the screening analysis:

```bash
curl -X POST http://localhost:8000/screenings/1/analysis \
  -H "Authorization: Bearer <token>"
```

## Roadmap

- add async audio transcription as a later milestone
