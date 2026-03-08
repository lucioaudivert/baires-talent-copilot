import asyncio

import httpx

from baires_talent_copilot.main import app


async def request(
    method: str,
    path: str,
    json: dict | None = None,
    token: str | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, json=json, headers=headers)


def register_token(
    *,
    display_name: str = "Lucio Recruiter",
    email: str = "lucio@example.com",
    password: str = "Talent1234!",
) -> str:
    response = asyncio.run(
        request(
            "POST",
            "/auth/register",
            json={
                "display_name": display_name,
                "email": email,
                "password": password,
            },
        )
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_auth_login_logout_and_protected_flow() -> None:
    protected_response = asyncio.run(request("GET", "/roles"))
    assert protected_response.status_code == 401

    token = register_token()

    me_response = asyncio.run(request("GET", "/auth/me", token=token))
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "lucio@example.com"

    role_response = asyncio.run(
        request(
            "POST",
            "/roles",
            json={
                "title": "LLM Operations Analyst",
                "seniority": "mid",
                "language": "es",
                "summary": "Help screening AI operations profiles.",
                "must_have_skills": ["Python", "FastAPI", "LLMs"],
                "nice_to_have_skills": ["Prompt design"],
            },
            token=token,
        )
    )
    assert role_response.status_code == 201
    role_id = role_response.json()["id"]

    screening_response = asyncio.run(
        request(
            "POST",
            "/screenings",
            json={
                "role_id": role_id,
                "candidate_name": "Ana Lopez",
                "candidate_email": "ana@example.com",
                "intro_notes": "Referral from a client contact.",
            },
            token=token,
        )
    )
    assert screening_response.status_code == 201
    screening_id = screening_response.json()["id"]

    asyncio.run(
        request(
            "POST",
            f"/screenings/{screening_id}/messages",
            json={
                "speaker": "candidate",
                "content": "I work with Python and FastAPI building workflow tools.",
            },
            token=token,
        )
    )

    asyncio.run(
        request(
            "POST",
            f"/screenings/{screening_id}/messages",
            json={
                "speaker": "candidate",
                "content": "I also evaluate LLM outputs and define metrics for quality.",
            },
            token=token,
        )
    )

    analysis_response = asyncio.run(
        request("POST", f"/screenings/{screening_id}/analysis", token=token)
    )
    assert analysis_response.status_code == 201
    analysis = analysis_response.json()
    assert analysis["analysis_source"] == "heuristic"
    assert analysis["recommended_status"] == "review_ready"
    assert analysis["matched_skills"] == ["Python", "FastAPI", "LLMs"]

    detail_response = asyncio.run(request("GET", f"/screenings/{screening_id}", token=token))
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["latest_analysis"]["analysis_source"] == "heuristic"
    assert [event["event_type"] for event in detail["audit_events"]] == [
        "screening_created",
        "message_added",
        "message_added",
        "analysis_generated",
    ]
    assert detail["audit_events"][0]["actor_label"] == "Lucio Recruiter"
    assert detail["audit_events"][-1]["payload"]["recommended_status"] == "review_ready"

    audit_response = asyncio.run(
        request("GET", f"/screenings/{screening_id}/audit", token=token)
    )
    assert audit_response.status_code == 200
    assert audit_response.json() == detail["audit_events"]

    status_update_response = asyncio.run(
        request(
            "PATCH",
            f"/screenings/{screening_id}/status",
            json={"status": "draft"},
            token=token,
        )
    )
    assert status_update_response.status_code == 200
    assert status_update_response.json()["status"] == "draft"

    status_detail_response = asyncio.run(
        request("GET", f"/screenings/{screening_id}", token=token)
    )
    assert status_detail_response.status_code == 200
    status_detail = status_detail_response.json()
    assert status_detail["status"] == "draft"
    assert status_detail["audit_events"][-1]["event_type"] == "status_changed"
    assert status_detail["audit_events"][-1]["payload"] == {
        "from_status": "review_ready",
        "to_status": "draft",
    }

    third_message_response = asyncio.run(
        request(
            "POST",
            f"/screenings/{screening_id}/messages",
            json={
                "speaker": "recruiter",
                "content": "Can you share a recent example working with stakeholders?",
            },
            token=token,
        )
    )
    assert third_message_response.status_code == 201

    refreshed_detail_response = asyncio.run(
        request("GET", f"/screenings/{screening_id}", token=token)
    )
    assert refreshed_detail_response.status_code == 200
    refreshed_detail = refreshed_detail_response.json()
    assert refreshed_detail["latest_analysis"] is None
    assert refreshed_detail["status"] == "in_progress"
    assert [event["event_type"] for event in refreshed_detail["audit_events"][-3:]] == [
        "status_changed",
        "message_added",
        "analysis_cleared",
    ]

    logout_response = asyncio.run(request("POST", "/auth/logout", token=token))
    assert logout_response.status_code == 204

    expired_response = asyncio.run(request("GET", "/roles", token=token))
    assert expired_response.status_code == 401


def test_recruiters_are_data_isolated() -> None:
    recruiter_one = register_token(
        display_name="Recruiter One",
        email="one@example.com",
    )
    recruiter_two = register_token(
        display_name="Recruiter Two",
        email="two@example.com",
    )

    role_response = asyncio.run(
        request(
            "POST",
            "/roles",
            json={
                "title": "Private Role",
                "seniority": "senior",
                "language": "es",
                "summary": "Visible only to recruiter one.",
                "must_have_skills": ["Python"],
                "nice_to_have_skills": [],
            },
            token=recruiter_one,
        )
    )
    role_id = role_response.json()["id"]

    screening_response = asyncio.run(
        request(
            "POST",
            "/screenings",
            json={
                "role_id": role_id,
                "candidate_name": "Hidden Candidate",
                "candidate_email": "hidden@example.com",
                "intro_notes": "Should not leak.",
            },
            token=recruiter_one,
        )
    )
    screening_id = screening_response.json()["id"]

    recruiter_two_roles = asyncio.run(request("GET", "/roles", token=recruiter_two))
    assert recruiter_two_roles.status_code == 200
    assert recruiter_two_roles.json() == []

    recruiter_two_screening = asyncio.run(
        request("GET", f"/screenings/{screening_id}", token=recruiter_two)
    )
    assert recruiter_two_screening.status_code == 404

    recruiter_two_status_patch = asyncio.run(
        request(
            "PATCH",
            f"/screenings/{screening_id}/status",
            json={"status": "review_ready"},
            token=recruiter_two,
        )
    )
    assert recruiter_two_status_patch.status_code == 404


def test_demo_bootstrap_is_idempotent_for_authenticated_user() -> None:
    token = register_token()

    config_response = asyncio.run(request("GET", "/auth/config"))
    assert config_response.status_code == 200
    assert config_response.json()["demo_account_enabled"] is True

    first_bootstrap_response = asyncio.run(
        request("POST", "/demo/bootstrap", token=token)
    )
    assert first_bootstrap_response.status_code == 201
    first_payload = first_bootstrap_response.json()

    second_bootstrap_response = asyncio.run(
        request("POST", "/demo/bootstrap", token=token)
    )
    assert second_bootstrap_response.status_code == 201
    second_payload = second_bootstrap_response.json()

    assert first_payload["id"] == second_payload["id"]
    assert first_payload["latest_analysis"]["analysis_source"] == "heuristic"
    assert [event["event_type"] for event in first_payload["audit_events"]] == [
        "screening_created",
        "message_added",
        "message_added",
        "message_added",
        "analysis_generated",
        "demo_bootstrapped",
    ]
    assert first_payload["audit_events"] == second_payload["audit_events"]


def test_demo_recruiter_can_log_in() -> None:
    config_response = asyncio.run(request("GET", "/auth/config"))
    config_payload = config_response.json()

    login_response = asyncio.run(
        request(
            "POST",
            "/auth/login",
            json={
                "email": config_payload["demo_email"],
                "password": config_payload["demo_password"],
            },
        )
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["display_name"] == config_payload["demo_display_name"]
