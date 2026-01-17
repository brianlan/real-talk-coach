from __future__ import annotations

import httpx
import pytest

from app.api.routes import evaluations as evaluations_routes
from app.main import app
from app.repositories.evaluation_repository import EvaluationRecord
from app.repositories.session_repository import PracticeSessionRecord


@pytest.mark.asyncio
async def test_evaluation_get_emits_queue_latency(monkeypatch):
    calls = []

    def fake_emit_metric(name, value, **kwargs):
        calls.append((name, value, kwargs))

    monkeypatch.setattr(evaluations_routes, "emit_metric", fake_emit_metric)
    monkeypatch.setattr(evaluations_routes, "enqueue", lambda *_args, **_kwargs: None)

    async def _get_session(session_id: str):
        return PracticeSessionRecord(
            id=session_id,
            scenario_id="scenario-1",
            stub_user_id="pilot-user",
            status="ended",
            client_session_started_at="2025-01-01T00:00:00Z",
            started_at="2025-01-01T00:00:00Z",
            ended_at="2025-01-01T00:10:00Z",
            total_duration_seconds=600,
            idle_limit_seconds=8,
            duration_limit_seconds=300,
            ws_channel=f"/ws/sessions/{session_id}",
            objective_status="unknown",
            objective_reason=None,
            termination_reason="manual",
            evaluation_id="eval-1",
        )

    async def _get_by_session(session_id: str):
        return EvaluationRecord(
            id="eval-1",
            session_id=session_id,
            status="completed",
            scores=[],
            summary="ok",
            evaluator_model="gpt-5-mini",
            attempts=1,
            last_error=None,
            queued_at="2025-01-01T00:00:00+00:00",
            completed_at="2025-01-01T00:00:10+00:00",
        )

    class FakeSessionRepo:
        get_session = staticmethod(_get_session)

    class FakeEvaluationRepo:
        get_by_session = staticmethod(_get_by_session)

    app.dependency_overrides[evaluations_routes._session_repo] = lambda: FakeSessionRepo()
    app.dependency_overrides[evaluations_routes._evaluation_repo] = lambda: FakeEvaluationRepo()

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
        response = await client.get("/api/sessions/session-1/evaluation")

    assert response.status_code == 200
    assert calls
    assert calls[0][0] == "evaluation.queue_latency"

    app.dependency_overrides.pop(evaluations_routes._session_repo, None)
    app.dependency_overrides.pop(evaluations_routes._evaluation_repo, None)
