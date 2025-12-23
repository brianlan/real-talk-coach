from datetime import datetime, timezone

import pytest

from app.api.routes import sessions as sessions_routes
from app.api.routes import turns as turns_routes
from app.repositories.session_repository import PracticeSessionRecord, TurnRecord


@pytest.mark.asyncio
async def test_session_create_starts_span(monkeypatch):
    spans = []

    def fake_start_span(name, attributes=None):
        spans.append((name, attributes))
        class Dummy:
            def __enter__(self_inner):
                return None
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return Dummy()

    async def _create_session(payload):
        return PracticeSessionRecord(
            id="session-1",
            scenario_id=payload["scenarioId"],
            stub_user_id=payload["stubUserId"],
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
        )

    async def _update_session(session_id, payload):
        return PracticeSessionRecord(
            id=session_id,
            scenario_id="scenario-1",
            stub_user_id="pilot-user",
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
        )

    class FakeRepo:
        create_session = staticmethod(_create_session)
        update_session = staticmethod(_update_session)
        list_sessions = staticmethod(lambda stub_user_id=None: _list_sessions())
        add_turn = staticmethod(lambda payload: _add_turn(payload))

    async def _list_sessions():
        return []

    async def _add_turn(payload):
        return TurnRecord(
            id="turn-0",
            session_id=payload["sessionId"],
            sequence=payload["sequence"],
            speaker=payload["speaker"],
            transcript=payload["transcript"],
            audio_file_id=payload["audioFileId"],
            audio_url=payload["audioUrl"],
            asr_status=payload["asrStatus"],
            created_at=payload["createdAt"],
            started_at=payload["startedAt"],
            ended_at=payload["endedAt"],
            context=payload.get("context"),
            latency_ms=payload.get("latencyMs"),
        )

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return type("Scenario", (), {"prompt": "Hello"})()

    monkeypatch.setattr(sessions_routes, "start_span", fake_start_span)

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

    payload = sessions_routes.PracticeSessionCreate(
        scenarioId="scenario-1",
        clientSessionStartedAt=datetime.now(timezone.utc).isoformat(),
    )

    await sessions_routes.create_session(
        payload,
        repo=FakeRepo(),
        scenario_repo=FakeScenarioRepo(),
    )

    assert spans
    assert spans[0][0] == "sessions.create"


@pytest.mark.asyncio
async def test_turn_create_starts_span(monkeypatch):
    spans = []

    def fake_start_span(name, attributes=None):
        spans.append((name, attributes))
        class Dummy:
            def __enter__(self_inner):
                return None
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return Dummy()

    async def _get_session(session_id):
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

    async def _list_turns(session_id):
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

    async def _noop_pipeline(*args, **kwargs):
        return None

    monkeypatch.setattr(turns_routes, "start_span", fake_start_span)
    monkeypatch.setattr(turns_routes, "enqueue_turn_pipeline", _noop_pipeline)

    now = datetime.now(timezone.utc)
    payload = turns_routes.TurnInput(
        sequence=0,
        audioBase64="YQ==",
        startedAt=now,
        endedAt=now,
    )

    await turns_routes.submit_turn("session-1", payload, repo=FakeRepo())

    assert spans
    assert spans[0][0] == "turns.create"
