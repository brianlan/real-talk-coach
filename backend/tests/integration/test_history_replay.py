from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from app.api.routes import history as history_routes
from app.api.routes import sessions as sessions_routes
from app.main import app
from app.repositories.session_repository import PracticeSessionRecord, TurnRecord


@pytest.mark.asyncio
async def test_history_detail_and_practice_again_emit_step_metric(monkeypatch):
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

    metrics = []

    def fake_emit_metric(name, value, **kwargs):
        metrics.append((name, value, kwargs))

    monkeypatch.setattr(history_routes, "emit_metric", fake_emit_metric)

    base_session = PracticeSessionRecord(
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
    sessions = {"session-1": base_session}
    turns = [
        TurnRecord(
            id="turn-1",
            session_id="session-1",
            sequence=0,
            speaker="ai",
            transcript="Hi",
            audio_file_id="file-1",
            audio_url="https://files/turn-1.mp3",
            asr_status=None,
            created_at=None,
            started_at=None,
            ended_at=None,
            context=None,
            latency_ms=None,
        )
    ]

    class FakeSessionRepo:
        async def list_sessions(self, stub_user_id=None):
            return list(sessions.values())

        async def get_session(self, session_id: str):
            return sessions.get(session_id)

        async def list_turns(self, session_id: str):
            return turns

        async def create_session(self, payload: dict):
            record = PracticeSessionRecord(
                id="session-new",
                scenario_id=payload.get("scenarioId", ""),
                stub_user_id=payload.get("stubUserId", ""),
                status=payload.get("status", "pending"),
                client_session_started_at=payload.get("clientSessionStartedAt", ""),
                started_at=payload.get("startedAt"),
                ended_at=payload.get("endedAt"),
                total_duration_seconds=payload.get("totalDurationSeconds"),
                idle_limit_seconds=payload.get("idleLimitSeconds"),
                duration_limit_seconds=payload.get("durationLimitSeconds"),
                ws_channel=payload.get("wsChannel", ""),
                objective_status=payload.get("objectiveStatus", "unknown"),
                objective_reason=payload.get("objectiveReason"),
                termination_reason=payload.get("terminationReason"),
                evaluation_id=payload.get("evaluationId"),
            )
            sessions[record.id] = record
            return record

        async def update_session(self, session_id: str, payload: dict):
            record = sessions.get(session_id)
            if not record:
                return None
            updated = PracticeSessionRecord(
                id=record.id,
                scenario_id=record.scenario_id,
                stub_user_id=record.stub_user_id,
                status=payload.get("status", record.status),
                client_session_started_at=record.client_session_started_at,
                started_at=record.started_at,
                ended_at=payload.get("endedAt", record.ended_at),
                total_duration_seconds=record.total_duration_seconds,
                idle_limit_seconds=record.idle_limit_seconds,
                duration_limit_seconds=record.duration_limit_seconds,
                ws_channel=payload.get("wsChannel", record.ws_channel),
                objective_status=record.objective_status,
                objective_reason=record.objective_reason,
                termination_reason=payload.get("terminationReason", record.termination_reason),
                evaluation_id=record.evaluation_id,
            )
            sessions[record.id] = updated
            return updated

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return type(
                "Scenario",
                (),
                {
                    "id": scenario_id,
                    "category": "Feedback",
                    "title": "Scenario",
                    "description": "desc",
                    "objective": "Objective",
                    "ai_persona": {"name": "AI", "background": "Background"},
                    "trainee_persona": {"name": "Trainee", "background": "Background"},
                    "end_criteria": ["done"],
                    "skills": [],
                    "skill_summaries": [],
                    "idle_limit_seconds": 8,
                    "duration_limit_seconds": 300,
                    "prompt": "Prompt",
                    "status": "published",
                },
            )()

    class FakeEvaluationRepo:
        async def get_by_session(self, session_id: str):
            return None

    class FakeSigningClient:
        async def create_signed_urls(self, urls, ttl_seconds=900):
            return {url: f"{url}?signed=1" for url in urls}

    async def _noop_initial_turn(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.turn_pipeline.generate_initial_ai_turn",
        _noop_initial_turn,
    )

    app.dependency_overrides[history_routes._session_repo] = lambda: FakeSessionRepo()
    app.dependency_overrides[history_routes._scenario_repo] = lambda: FakeScenarioRepo()
    app.dependency_overrides[history_routes._evaluation_repo] = lambda: FakeEvaluationRepo()
    app.dependency_overrides[history_routes._signing_client] = lambda: FakeSigningClient()
    app.dependency_overrides[sessions_routes._repo] = lambda: FakeSessionRepo()
    app.dependency_overrides[sessions_routes._scenario_repo] = lambda: FakeScenarioRepo()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/sessions/session-1", params={"historyStepCount": 2}
        )
        assert response.status_code == 200
        detail = response.json()
        assert detail["turns"][0]["audioUrl"].endswith("?signed=1")

        response = await client.post(
            "/api/sessions/session-1/practice-again",
            json={"clientSessionStartedAt": datetime.now(timezone.utc).isoformat()},
        )
        assert response.status_code == 201

    assert any(metric[0] == "history.step_count" for metric in metrics)
    app.dependency_overrides.pop(history_routes._session_repo, None)
    app.dependency_overrides.pop(history_routes._scenario_repo, None)
    app.dependency_overrides.pop(history_routes._evaluation_repo, None)
    app.dependency_overrides.pop(history_routes._signing_client, None)
    app.dependency_overrides.pop(sessions_routes._repo, None)
    app.dependency_overrides.pop(sessions_routes._scenario_repo, None)
