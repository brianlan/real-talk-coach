from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from fastapi import status

from app.api.routes import history as history_routes
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
    monkeypatch.setenv("ADMIN_ACCESS_TOKEN", "token")


def _session(session_id: str, started_at: str, scenario_id: str = "scenario-1"):
    return PracticeSessionRecord(
        id=session_id,
        scenario_id=scenario_id,
        stub_user_id="pilot-user",
        status="ended",
        client_session_started_at=started_at,
        started_at=started_at,
        ended_at=started_at,
        total_duration_seconds=60,
        idle_limit_seconds=8,
        duration_limit_seconds=300,
        ws_channel=f"/ws/sessions/{session_id}",
        objective_status="unknown",
        objective_reason=None,
        termination_reason="manual",
        evaluation_id=None,
    )


@pytest.mark.asyncio
async def test_history_requires_step_count(monkeypatch):
    class FakeRepo:
        list_sessions = staticmethod(lambda stub_user_id=None: [])

    app.dependency_overrides[history_routes._session_repo] = lambda: FakeRepo()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sessions")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    app.dependency_overrides.pop(history_routes._session_repo, None)


@pytest.mark.asyncio
async def test_history_default_sort_and_page_size(monkeypatch):
    sessions = [
        _session("session-1", "2025-01-01T00:00:00Z"),
        _session("session-2", "2025-01-02T00:00:00Z"),
    ] + [
        _session(f"session-{i}", "2025-01-03T00:00:00Z") for i in range(3, 25)
    ]

    class FakeRepo:
        list_sessions = staticmethod(lambda stub_user_id=None: sessions)

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return type(
                "Scenario",
                (),
                {
                    "category": "Feedback",
                    "title": "Difficult feedback",
                    "objective": "Provide clear feedback",
                },
            )()

    app.dependency_overrides[history_routes._session_repo] = lambda: FakeRepo()
    app.dependency_overrides[history_routes._scenario_repo] = lambda: FakeScenarioRepo()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sessions", params={"historyStepCount": 1})

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["pageSize"] == 20
    assert len(payload["items"]) == 20
    assert payload["items"][0]["id"] == "session-3"

    app.dependency_overrides.pop(history_routes._session_repo, None)
    app.dependency_overrides.pop(history_routes._scenario_repo, None)


@pytest.mark.asyncio
async def test_history_sort_ascending(monkeypatch):
    sessions = [
        _session("session-1", "2025-01-02T00:00:00Z"),
        _session("session-2", "2025-01-01T00:00:00Z"),
    ]

    class FakeRepo:
        list_sessions = staticmethod(lambda stub_user_id=None: sessions)

    app.dependency_overrides[history_routes._session_repo] = lambda: FakeRepo()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/sessions",
            params={"historyStepCount": 1, "sort": "startedAtAsc"},
        )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["items"][0]["id"] == "session-2"
    app.dependency_overrides.pop(history_routes._session_repo, None)


@pytest.mark.asyncio
async def test_history_filtering_by_category_and_search(monkeypatch):
    sessions = [
        _session("session-1", "2025-01-01T00:00:00Z", "scenario-1"),
        _session("session-2", "2025-01-01T00:00:00Z", "scenario-2"),
    ]

    class FakeRepo:
        list_sessions = staticmethod(lambda stub_user_id=None: sessions)

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            if scenario_id == "scenario-1":
                return type(
                    "Scenario",
                    (),
                    {
                        "category": "Feedback",
                        "title": "Difficult feedback",
                        "objective": "Provide clear feedback",
                    },
                )()
            return type(
                "Scenario",
                (),
                {
                    "category": "Conflict",
                    "title": "Hard conversation",
                    "objective": "Resolve tension",
                },
            )()

    app.dependency_overrides[history_routes._session_repo] = lambda: FakeRepo()
    app.dependency_overrides[history_routes._scenario_repo] = lambda: FakeScenarioRepo()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/sessions",
            params={"historyStepCount": 1, "category": "Feedback", "search": "difficult"},
        )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == "session-1"

    app.dependency_overrides.pop(history_routes._session_repo, None)
    app.dependency_overrides.pop(history_routes._scenario_repo, None)


@pytest.mark.asyncio
async def test_delete_session_calls_cleanup(monkeypatch):
    called = {"count": 0}

    async def fake_cleanup(session_id: str):
        called["count"] += 1

    async def _get_session(session_id: str):
        return _session(session_id, datetime.now(timezone.utc).isoformat())

    class FakeRepo:
        get_session = staticmethod(_get_session)

    app.dependency_overrides[sessions_routes._repo] = lambda: FakeRepo()
    monkeypatch.setattr(sessions_routes, "cleanup_session", fake_cleanup)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/sessions/session-1")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert called["count"] == 1
    app.dependency_overrides.pop(sessions_routes._repo, None)
