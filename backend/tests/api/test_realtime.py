from __future__ import annotations

import httpx
import pytest
from fastapi import status
from typing import Literal

from app.clients.volcengine_rtc import VolcengineAPIError
from app.main import app
from app.repositories.session_repository import PracticeSessionRecord


def _make_session(
    session_id: str = "session-1",
    rtc_room_id: str | None = None,
    rtc_task_id: str | None = None,
    realtime_state: Literal["connecting", "active", "ended"] | None = None,
) -> PracticeSessionRecord:
    return PracticeSessionRecord(
        id=session_id,
        scenario_id="scenario-1",
        stub_user_id="user-1",
        language="en",
        opening_prompt="Hello",
        status="active",
        client_session_started_at="2025-01-01T00:00:00Z",
        started_at="2025-01-01T00:00:00Z",
        ended_at=None,
        total_duration_seconds=60,
        idle_limit_seconds=30,
        duration_limit_seconds=300,
        ws_channel="channel-1",
        objective_status="pending",
        objective_reason=None,
        termination_reason=None,
        evaluation_id=None,
        rtc_room_id=rtc_room_id,
        rtc_task_id=rtc_task_id,
        realtime_state=realtime_state,
    )


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("LEAN_APP_ID", "app")
    monkeypatch.setenv("LEAN_APP_KEY", "key")
    monkeypatch.setenv("LEAN_MASTER_KEY", "master")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash")
    monkeypatch.setenv("CHATAI_API_BASE", "https://api.chataiapi.com/v1")
    monkeypatch.setenv("CHATAI_API_KEY", "secret")
    monkeypatch.setenv("CHATAI_API_MODEL", "gpt-5-mini")
    monkeypatch.setenv("EVALUATOR_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OBJECTIVE_CHECK_API_KEY", "secret")
    monkeypatch.setenv("OBJECTIVE_CHECK_MODEL", "gpt-5-mini")
    monkeypatch.setenv("STUB_USER_ID", "pilot-user")
    monkeypatch.setenv("ADMIN_ACCESS_TOKEN", "admin-token")
    monkeypatch.setenv("VOLCENGINE_ACCESS_KEY_ID", "ak-test")
    monkeypatch.setenv("VOLCENGINE_SECRET_ACCESS_KEY", "sk-test")
    monkeypatch.setenv("VOLCENGINE_RTC_APP_ID", "app-test")
    monkeypatch.setenv("VOLCENGINE_RTC_APP_KEY", "app-key-test")
    monkeypatch.setenv("VOLCENGINE_VOICE_CHAT_ENDPOINT", "https://rtc.volcengineapi.com")
    monkeypatch.setenv("VOLCENGINE_VOICE_MODEL_ID", "doubao-voice-realtime")


@pytest.fixture
def mock_session_repo(monkeypatch):
    test_session = _make_session(
        session_id="session-1",
        rtc_room_id="room-1",
        rtc_task_id="task-1",
        realtime_state="active",
    )
    updated_session = None

    async def _get_session(session_id: str):
        if session_id == "session-1":
            return test_session
        if session_id == "session-no-rtc":
            return _make_session(session_id="session-no-rtc", rtc_room_id=None, rtc_task_id=None)
        if session_id == "session-no-task":
            return _make_session(
                session_id="session-no-task",
                rtc_room_id="room-2",
                rtc_task_id=None,
            )
        return None

    async def _update_session(session_id: str, payload: dict):
        nonlocal updated_session
        if session_id == "session-1":
            updated_session = PracticeSessionRecord(
                id=session_id,
                scenario_id=test_session.scenario_id,
                stub_user_id=test_session.stub_user_id,
                language=test_session.language,
                opening_prompt=test_session.opening_prompt,
                status=payload.get("status", test_session.status),
                client_session_started_at=test_session.client_session_started_at,
                started_at=test_session.started_at,
                ended_at=payload.get("endedAt", test_session.ended_at),
                total_duration_seconds=payload.get(
                    "totalDurationSeconds", test_session.total_duration_seconds
                ),
                idle_limit_seconds=test_session.idle_limit_seconds,
                duration_limit_seconds=test_session.duration_limit_seconds,
                ws_channel=payload.get("wsChannel", test_session.ws_channel),
                objective_status=test_session.objective_status,
                objective_reason=test_session.objective_reason,
                termination_reason=payload.get("terminationReason", test_session.termination_reason),
                evaluation_id=test_session.evaluation_id,
                mode=payload.get("mode", test_session.mode),
                rtc_room_id=payload.get("rtcRoomId", test_session.rtc_room_id),
                rtc_task_id=payload.get("rtcTaskId", test_session.rtc_task_id),
                realtime_state=payload.get("realtimeState", test_session.realtime_state),
            )
            return updated_session
        if session_id == "session-no-task":
            updated_session = _make_session(
                session_id="session-no-task",
                rtc_room_id="room-2",
                rtc_task_id=None,
                realtime_state=payload.get("realtimeState", "ended"),
            )
            return updated_session
        return None

    class FakeRepo:
        get_session = staticmethod(_get_session)
        update_session = staticmethod(_update_session)

    from app.api.routes import realtime as realtime_routes
    app.dependency_overrides[realtime_routes._repo] = lambda: FakeRepo()
    yield FakeRepo()
    app.dependency_overrides.pop(realtime_routes._repo, None)


@pytest.fixture
def mock_rtc_client(monkeypatch):
    from app.api.routes import realtime as realtime_routes

    class FakeRTCClient:
        def __init__(self, **kwargs):
            pass

        def generate_rtc_token(self, room_id: str, user_id: str) -> str:
            return f"mock-token-{room_id}-{user_id}"

        async def start_voice_chat(self, room_id: str, task_id: str, system_prompt: str) -> dict:
            return {"Result": {"TaskState": "started"}}

        async def stop_voice_chat(self, room_id: str, task_id: str) -> dict:
            return {"Result": {"TaskState": "stopped"}}

        async def close(self):
            pass

    async def _rtc_client_generator():
        yield FakeRTCClient()

    app.dependency_overrides[realtime_routes._rtc_client] = _rtc_client_generator
    yield FakeRTCClient()
    app.dependency_overrides.pop(realtime_routes._rtc_client, None)


@pytest.mark.asyncio
async def test_create_realtime_token_success(mock_session_repo, mock_rtc_client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/realtime/token",
            json={"session_id": "session-1", "user_id": "user-1"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "token" in data
    assert data["token"] == "mock-token-room-1-user-1"
    assert data["room_id"] == "room-1"
    assert data["app_id"] == "app-test"


@pytest.mark.asyncio
async def test_create_realtime_token_session_not_found(mock_session_repo, mock_rtc_client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/realtime/token",
            json={"session_id": "nonexistent", "user_id": "user-1"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Session not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_start_realtime_chat_success(mock_session_repo, mock_rtc_client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/realtime/start",
            json={"session_id": "session-1", "system_prompt": "You are a helpful assistant."},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["session_id"] == "session-1"
    assert data["room_id"] == "room-1"
    assert data["rtc_task_id"] == "task-1"
    assert data["realtime_state"] == "active"


@pytest.mark.asyncio
async def test_start_realtime_chat_session_not_found(mock_session_repo, mock_rtc_client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/realtime/start",
            json={"session_id": "nonexistent", "system_prompt": "Prompt"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Session not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_start_realtime_chat_rtc_error(mock_session_repo):
    from app.api.routes import realtime as realtime_routes

    class FailingRTCClient:
        def __init__(self, **kwargs):
            pass

        async def start_voice_chat(self, room_id: str, task_id: str, system_prompt: str):
            raise VolcengineAPIError("API Error", status_code=500)

        async def close(self):
            pass

    async def _failing_rtc_client_generator():
        yield FailingRTCClient()

    app.dependency_overrides[realtime_routes._rtc_client] = _failing_rtc_client_generator

    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/realtime/start",
                json={"session_id": "session-1", "system_prompt": "Prompt"},
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
    finally:
        app.dependency_overrides.pop(realtime_routes._rtc_client, None)


@pytest.mark.asyncio
async def test_stop_realtime_chat_success(mock_session_repo, mock_rtc_client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/realtime/stop",
            json={"session_id": "session-1"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["session_id"] == "session-1"
    assert data["realtime_state"] == "ended"


@pytest.mark.asyncio
async def test_stop_realtime_chat_session_not_found(mock_session_repo, mock_rtc_client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/realtime/stop",
            json={"session_id": "nonexistent"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_stop_realtime_chat_no_active_task(mock_session_repo, mock_rtc_client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/realtime/stop",
            json={"session_id": "session-no-task"},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "no active realtime task" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stop_realtime_chat_rtc_error(mock_session_repo):
    from app.api.routes import realtime as realtime_routes

    class FailingRTCClient:
        def __init__(self, **kwargs):
            pass

        async def stop_voice_chat(self, room_id: str, task_id: str):
            raise VolcengineAPIError("API Error", status_code=500)

        async def close(self):
            pass

    async def _failing_rtc_client_generator():
        yield FailingRTCClient()

    app.dependency_overrides[realtime_routes._rtc_client] = _failing_rtc_client_generator

    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/realtime/stop",
                json={"session_id": "session-1"},
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
    finally:
        app.dependency_overrides.pop(realtime_routes._rtc_client, None)
