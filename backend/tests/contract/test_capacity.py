import httpx
import pytest
from fastapi import status

from app.api.routes import sessions as sessions_routes
from app.main import app
from app.repositories.session_repository import PracticeSessionRecord


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


def _session(status_value: str) -> PracticeSessionRecord:
    return PracticeSessionRecord(
        id=f"session-{status_value}",
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        status=status_value,
        client_session_started_at="2025-01-01T00:00:00Z",
        started_at="2025-01-01T00:00:00Z",
        ended_at=None,
        total_duration_seconds=None,
        idle_limit_seconds=8,
        duration_limit_seconds=300,
        ws_channel=f"/ws/sessions/session-{status_value}",
        objective_status="unknown",
        objective_reason=None,
        termination_reason=None,
        evaluation_id=None,
    )


@pytest.mark.asyncio
async def test_capacity_limit_returns_429(monkeypatch):
    async def _list_sessions(stub_user_id=None):
        return [_session("active")] * 20

    class FakeRepo:
        list_sessions = staticmethod(_list_sessions)
        create_session = staticmethod(lambda payload: _session("pending"))
        update_session = staticmethod(lambda session_id, payload: _session("pending"))

    app.dependency_overrides[sessions_routes._repo] = lambda: FakeRepo()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": "2025-01-01T00:00:00Z",
            },
        )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "pilot capacity exceeded" in response.text

    app.dependency_overrides.pop(sessions_routes._repo, None)


@pytest.mark.asyncio
async def test_pending_limit_returns_429(monkeypatch):
    async def _list_sessions(stub_user_id=None):
        return [_session("pending")] * 5

    class FakeRepo:
        list_sessions = staticmethod(_list_sessions)
        create_session = staticmethod(lambda payload: _session("pending"))
        update_session = staticmethod(lambda session_id, payload: _session("pending"))

    app.dependency_overrides[sessions_routes._repo] = lambda: FakeRepo()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": "2025-01-01T00:00:00Z",
            },
        )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "pilot capacity exceeded" in response.text

    app.dependency_overrides.pop(sessions_routes._repo, None)
