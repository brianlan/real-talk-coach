from datetime import datetime, timezone

from fastapi import BackgroundTasks

import pytest

from app.api.routes import sessions as sessions_routes
from app.repositories.session_repository import PracticeSessionRecord


@pytest.mark.asyncio
async def test_session_create_starts_span(monkeypatch):
    spans = []

    def fake_start_span(name, attributes=None):
        spans.append((name, attributes))

        class Dummy:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, tb):
                return False

        return Dummy()

    async def _create_session(payload):
        return PracticeSessionRecord(
            id="session-1",
            scenario_id=payload["scenarioId"],
            stub_user_id=payload["stubUserId"],
            language=payload.get("language", "en"),
            opening_prompt=payload.get("openingPrompt", "Hello"),
            status=payload["status"],
            client_session_started_at=payload["clientSessionStartedAt"],
            started_at=payload["startedAt"],
            ended_at=payload["endedAt"],
            total_duration_seconds=payload["totalDurationSeconds"],
            idle_limit_seconds=payload["idleLimitSeconds"],
            duration_limit_seconds=payload["durationLimitSeconds"],
            ws_channel=payload["wsChannel"],
            objective_status=payload["objectiveStatus"],
            objective_reason=payload["objectiveReason"],
            termination_reason=payload["terminationReason"],
            evaluation_id=payload["evaluationId"],
            mode=payload.get("mode", "realtime"),
        )

    async def _update_session(session_id, payload):
        return PracticeSessionRecord(
            id=session_id,
            scenario_id="scenario-1",
            stub_user_id="pilot-user",
            language="en",
            opening_prompt="Hello",
            status=payload.get("status", "pending"),
            client_session_started_at=payload.get("clientSessionStartedAt", ""),
            started_at=payload.get("startedAt"),
            ended_at=payload.get("endedAt"),
            total_duration_seconds=payload.get("totalDurationSeconds"),
            idle_limit_seconds=payload.get("idleLimitSeconds"),
            duration_limit_seconds=payload.get("durationLimitSeconds"),
            ws_channel=payload.get("wsChannel", "/ws/sessions/session-1"),
            objective_status=payload.get("objectiveStatus", "unknown"),
            objective_reason=payload.get("objectiveReason"),
            termination_reason=payload.get("terminationReason"),
            evaluation_id=payload.get("evaluationId"),
            mode=payload.get("mode", "realtime"),
        )

    async def _list_sessions():
        return []

    class FakeRepo:
        create_session = staticmethod(_create_session)
        update_session = staticmethod(_update_session)
        list_sessions = staticmethod(lambda stub_user_id=None: _list_sessions())

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return type(
                "Scenario",
                (),
                {
                    "id": scenario_id,
                    "metadata": {"title": "Span Scenario"},
                    "context": {"situation": "Span capture"},
                    "simulation_config": {
                        "ai": {"name": "AI", "background": "Background"},
                        "trainee": {"name": "Trainee", "background": "Background"},
                    },
                    "evaluation_config": {},
                    "status": "published",
                    "idle_limit_seconds": 8,
                    "duration_limit_seconds": 300,
                },
            )()

    monkeypatch.setattr(sessions_routes, "start_span", fake_start_span)

    monkeypatch.setenv("LEAN_APP_ID", "app")
    monkeypatch.setenv("LEAN_APP_KEY", "key")
    monkeypatch.setenv("LEAN_MASTER_KEY", "master")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_BASE", "https://api.chataiapi.com/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "secret")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_MODEL", "gpt-5-mini")
    monkeypatch.setenv("EVALUATOR_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OBJECTIVE_CHECK_API_KEY", "secret")
    monkeypatch.setenv("OBJECTIVE_CHECK_MODEL", "gpt-5-mini")
    monkeypatch.setenv("STUB_USER_ID", "pilot-user")

    payload = sessions_routes.PracticeSessionCreate(
        scenarioId="scenario-1",
        clientSessionStartedAt=datetime.now(timezone.utc),
    )

    await sessions_routes.create_session(
        payload,
        background_tasks=BackgroundTasks(),
        repo=FakeRepo(),  # pyright: ignore[reportArgumentType]
        scenario_repo=FakeScenarioRepo(),  # pyright: ignore[reportArgumentType]
    )

    assert spans
    assert spans[0][0] == "sessions.create"
