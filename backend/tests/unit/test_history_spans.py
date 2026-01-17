from __future__ import annotations

import httpx
import pytest

from app.api.routes import history as history_routes
from app.main import app
from app.repositories.session_repository import PracticeSessionRecord


@pytest.mark.asyncio
async def test_history_list_span_attributes(monkeypatch):
    spans = []

    def fake_start_span(name, attributes=None):
        spans.append((name, attributes))
        class Dummy:
            def __enter__(self_inner):
                return None
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return Dummy()

    monkeypatch.setattr(history_routes, "start_span", fake_start_span)
    monkeypatch.setattr(history_routes, "emit_metric", lambda *args, **kwargs: None)

    async def _list_sessions(stub_user_id=None):
        return [
            PracticeSessionRecord(
                id="session-1",
                scenario_id="scenario-1",
                stub_user_id="pilot-user",
                status="ended",
                client_session_started_at="2025-01-01T00:00:00Z",
                started_at="2025-01-01T00:00:00Z",
                ended_at="2025-01-01T00:10:00Z",
                total_duration_seconds=600,
                idle_limit_seconds=8,
                duration_limit_seconds=300,
                ws_channel="/ws/sessions/session-1",
                objective_status="unknown",
                objective_reason=None,
                termination_reason="manual",
                evaluation_id=None,
            )
        ]

    class FakeRepo:
        list_sessions = staticmethod(_list_sessions)

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return type(
                "Scenario",
                (),
                {
                    "category": "Feedback",
                    "title": "Growth",
                    "objective": "Grow",
                },
            )()

    app.dependency_overrides[history_routes._session_repo] = lambda: FakeRepo()
    app.dependency_overrides[history_routes._scenario_repo] = lambda: FakeScenarioRepo()

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

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/sessions",
            params={
                "historyStepCount": 1,
                "page": 2,
                "sort": "startedAtAsc",
                "category": "Feedback",
                "search": "growth",
            },
        )

    assert response.status_code == 200
    assert spans
    name, attrs = spans[0]
    assert name == "history.list"
    assert attrs["historyPage"] == 2
    assert attrs["sort"] == "startedAtAsc"
    assert attrs["category"] == "Feedback"
    assert attrs["search"] == "growth"

    app.dependency_overrides.pop(history_routes._session_repo, None)
    app.dependency_overrides.pop(history_routes._scenario_repo, None)
