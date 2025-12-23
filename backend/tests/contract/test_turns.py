from __future__ import annotations

import base64
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import status

from app.api.routes import turns as turns_routes
from app.main import app
from app.repositories.session_repository import PracticeSessionRecord, TurnRecord


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("LEAN_APP_ID", "app")
    monkeypatch.setenv("LEAN_APP_KEY", "key")
    monkeypatch.setenv("LEAN_MASTER_KEY", "master")
    monkeypatch.setenv("LEAN_SERVER_URL", "https://api.leancloud.cn")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash")
    monkeypatch.setenv("CHATAI_API_BASE", "https://api.chataiapi.com/v1")
    monkeypatch.setenv("CHATAI_API_KEY", "secret")
    monkeypatch.setenv("CHATAI_API_MODEL", "gpt-5-mini")
    monkeypatch.setenv("EVALUATOR_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OBJECTIVE_CHECK_API_KEY", "secret")
    monkeypatch.setenv("OBJECTIVE_CHECK_MODEL", "gpt-5-mini")
    monkeypatch.setenv("STUB_USER_ID", "pilot-user")


@pytest.fixture(autouse=True)
def _override_repo(monkeypatch):
    async def _get_session(session_id: str):
        return PracticeSessionRecord(
            id=session_id,
            scenario_id="scenario-1",
            stub_user_id="pilot-user",
            status="active",
            client_session_started_at="2025-01-01T00:00:00Z",
            started_at="2025-01-01T00:00:00Z",
            ended_at=None,
            total_duration_seconds=None,
            idle_limit_seconds=8,
            duration_limit_seconds=300,
            ws_channel=f"/ws/sessions/{session_id}",
            objective_status="unknown",
            objective_reason=None,
            termination_reason=None,
            evaluation_id=None,
        )

    async def _list_turns(session_id: str):
        return []

    async def _add_turn(payload):
        return TurnRecord(
            id="turn-1",
            session_id=payload["sessionId"],
            sequence=payload["sequence"],
            speaker=payload["speaker"],
            transcript=None,
            audio_file_id=payload["audioFileId"],
            audio_url=None,
            asr_status=payload["asrStatus"],
            created_at=payload["createdAt"],
            started_at=payload["startedAt"],
            ended_at=payload["endedAt"],
            context=payload.get("context"),
            latency_ms=None,
        )

    class FakeRepo:
        get_session = staticmethod(_get_session)
        list_turns = staticmethod(_list_turns)
        add_turn = staticmethod(_add_turn)

    app.dependency_overrides[turns_routes._repo] = lambda: FakeRepo()
    async def _noop_pipeline(*args, **kwargs):
        return None

    monkeypatch.setattr(turns_routes, "enqueue_turn_pipeline", _noop_pipeline)
    yield
    app.dependency_overrides.pop(turns_routes._repo, None)


def _audio_payload(size_bytes: int) -> str:
    return base64.b64encode(b"a" * size_bytes).decode("ascii")


@pytest.mark.asyncio
async def test_turn_submission_contract():
    now = datetime.now(timezone.utc)
    payload = {
        "sequence": 0,
        "audioBase64": _audio_payload(16),
        "startedAt": now.isoformat(),
        "endedAt": (now).isoformat(),
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/session-1/turns", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    receipt = response.json()
    assert receipt["sessionId"] == "session-1"
    assert "turnId" in receipt


@pytest.mark.asyncio
async def test_turn_rejects_oversized_audio():
    now = datetime.now(timezone.utc)
    payload = {
        "sequence": 0,
        "audioBase64": _audio_payload(131073),
        "startedAt": now.isoformat(),
        "endedAt": now.isoformat(),
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/session-1/turns", json=payload)

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    body = response.json()
    assert "128" in str(body).lower()


@pytest.mark.asyncio
async def test_turn_rejects_missing_timestamps():
    payload = {"sequence": 0, "audioBase64": _audio_payload(16)}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/session-1/turns", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_turn_rejects_missing_audio_guidance():
    now = datetime.now(timezone.utc)
    payload = {
        "sequence": 0,
        "audioBase64": "",
        "startedAt": now.isoformat(),
        "endedAt": now.isoformat(),
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/session-1/turns", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "resend" in response.text.lower()
