from __future__ import annotations

import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_practice_flow_turns_and_termination():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": "2025-01-01T00:00:00Z",
            },
        )
        assert response.status_code == 201
        session = response.json()

        turn_response = await client.post(
            f"/api/sessions/{session['id']}/turns",
            json={
                "sequence": 1,
                "audioBase64": "YQ==",
                "startedAt": "2025-01-01T00:00:00Z",
                "endedAt": "2025-01-01T00:00:01Z",
            },
        )
        assert turn_response.status_code == 202
        turn_receipt = turn_response.json()
        assert turn_receipt["sessionId"] == session["id"]

        stop_response = await client.post(
            f"/api/sessions/{session['id']}/manual-stop",
            json={"reason": "manual"},
        )
        assert stop_response.status_code == 202


@pytest.mark.asyncio
async def test_objective_check_outcomes_trigger_session_end():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": "2025-01-01T00:00:00Z",
            },
        )
        assert response.status_code == 201
        session = response.json()

        await client.post(
            f"/api/sessions/{session['id']}/turns",
            json={
                "sequence": 1,
                "audioBase64": "YQ==",
                "startedAt": "2025-01-01T00:00:00Z",
                "endedAt": "2025-01-01T00:00:01Z",
            },
        )

        await client.post(
            f"/api/sessions/{session['id']}/turns",
            json={
                "sequence": 2,
                "audioBase64": "YQ==",
                "startedAt": "2025-01-01T00:00:02Z",
                "endedAt": "2025-01-01T00:00:03Z",
                "context": "objective-check=pass",
            },
        )

        stop_response = await client.post(
            f"/api/sessions/{session['id']}/manual-stop",
            json={\"reason\": \"manual\"},
        )
        assert stop_response.status_code == 202


@pytest.mark.asyncio
async def test_qwen_outage_graceful_termination():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": "2025-01-01T00:00:00Z",
            },
        )
        assert response.status_code == 201
        session = response.json()

        turn_response = await client.post(
            f"/api/sessions/{session['id']}/turns",
            json={
                "sequence": 1,
                "audioBase64": "YQ==",
                "startedAt": "2025-01-01T00:00:00Z",
                "endedAt": "2025-01-01T00:00:01Z",
                "context": "force-qwen-outage",
            },
        )
        assert turn_response.status_code == 202

        stop_response = await client.post(
            f"/api/sessions/{session['id']}/manual-stop",
            json={\"reason\": \"qa_error\"},
        )
        assert stop_response.status_code == 202


@pytest.mark.asyncio
async def test_session_completion_enqueues_evaluation(monkeypatch):
    calls = {"count": 0}

    def fake_enqueue(session_id: str) -> None:
        calls["count"] += 1

    monkeypatch.setattr("app.tasks.evaluation_runner.enqueue", fake_enqueue)

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": "2025-01-01T00:00:00Z",
            },
        )
        assert response.status_code == 201
        session = response.json()

        stop_response = await client.post(
            f"/api/sessions/{session['id']}/manual-stop",
            json={\"reason\": \"manual\"},
        )
        assert stop_response.status_code == 202

    assert calls["count"] == 1
