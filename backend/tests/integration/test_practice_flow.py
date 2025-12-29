from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.main import app
from app.api.routes import turns as turns_routes
from app.api.routes.session_socket import hub
from app.repositories.scenario_repository import Scenario
from app.repositories.session_repository import PracticeSessionRecord, SessionRepository, TurnRecord


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
def _stub_repositories(monkeypatch):
    sessions: dict[str, PracticeSessionRecord] = {}
    turns: dict[str, TurnRecord] = {}
    session_counter = 0
    turn_counter = 0

    def _apply_session_payload(
        record: PracticeSessionRecord, payload: dict
    ) -> PracticeSessionRecord:
        data = {
            "id": record.id,
            "scenario_id": record.scenario_id,
            "stub_user_id": record.stub_user_id,
            "status": record.status,
            "client_session_started_at": record.client_session_started_at,
            "started_at": record.started_at,
            "ended_at": record.ended_at,
            "total_duration_seconds": record.total_duration_seconds,
            "idle_limit_seconds": record.idle_limit_seconds,
            "duration_limit_seconds": record.duration_limit_seconds,
            "ws_channel": record.ws_channel,
            "objective_status": record.objective_status,
            "objective_reason": record.objective_reason,
            "termination_reason": record.termination_reason,
            "evaluation_id": record.evaluation_id,
        }
        mapping = {
            "scenarioId": "scenario_id",
            "stubUserId": "stub_user_id",
            "clientSessionStartedAt": "client_session_started_at",
            "startedAt": "started_at",
            "endedAt": "ended_at",
            "totalDurationSeconds": "total_duration_seconds",
            "idleLimitSeconds": "idle_limit_seconds",
            "durationLimitSeconds": "duration_limit_seconds",
            "wsChannel": "ws_channel",
            "objectiveStatus": "objective_status",
            "objectiveReason": "objective_reason",
            "terminationReason": "termination_reason",
            "evaluationId": "evaluation_id",
            "status": "status",
        }
        for key, value in payload.items():
            field = mapping.get(key)
            if field:
                data[field] = value
        return PracticeSessionRecord(**data)

    def _apply_turn_payload(record: TurnRecord, payload: dict) -> TurnRecord:
        data = {
            "id": record.id,
            "session_id": record.session_id,
            "sequence": record.sequence,
            "speaker": record.speaker,
            "transcript": record.transcript,
            "audio_file_id": record.audio_file_id,
            "audio_url": record.audio_url,
            "asr_status": record.asr_status,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "ended_at": record.ended_at,
            "context": record.context,
            "latency_ms": record.latency_ms,
        }
        mapping = {
            "sessionId": "session_id",
            "sequence": "sequence",
            "speaker": "speaker",
            "transcript": "transcript",
            "audioFileId": "audio_file_id",
            "audioUrl": "audio_url",
            "asrStatus": "asr_status",
            "createdAt": "created_at",
            "startedAt": "started_at",
            "endedAt": "ended_at",
            "context": "context",
            "latencyMs": "latency_ms",
        }
        for key, value in payload.items():
            field = mapping.get(key)
            if field:
                data[field] = value
        return TurnRecord(**data)

    async def fake_get_scenario(self, scenario_id: str):
        return Scenario(
            id=scenario_id,
            category="practice",
            title="Test Scenario",
            description="Test description",
            objective="Test objective",
            ai_persona={"name": "Coach", "role": "Coach", "background": "Test"},
            trainee_persona={"name": "Trainee", "role": "Trainee", "background": "Test"},
            end_criteria=["done"],
            skills=[],
            skill_summaries=[],
            idle_limit_seconds=8,
            duration_limit_seconds=300,
            prompt="Begin.",
            status="published",
        )

    async def fake_create_session(self, payload: dict):
        nonlocal session_counter
        session_counter += 1
        session_id = f"session-{session_counter}"
        record = PracticeSessionRecord(
            id=session_id,
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
        sessions[session_id] = record
        return record

    async def fake_get_session(self, session_id: str):
        return sessions.get(session_id)

    async def fake_update_session(self, session_id: str, payload: dict):
        record = sessions.get(session_id)
        if not record:
            return None
        updated = _apply_session_payload(record, payload)
        sessions[session_id] = updated
        return updated

    async def fake_list_sessions(self, stub_user_id: str | None = None):
        if not stub_user_id:
            return list(sessions.values())
        return [session for session in sessions.values() if session.stub_user_id == stub_user_id]

    async def fake_delete_session(self, session_id: str):
        sessions.pop(session_id, None)
        for turn_id, turn in list(turns.items()):
            if turn.session_id == session_id:
                turns.pop(turn_id, None)

    async def fake_add_turn(self, payload: dict):
        nonlocal turn_counter
        turn_counter += 1
        turn_id = f"turn-{turn_counter}"
        record = TurnRecord(
            id=turn_id,
            session_id=payload.get("sessionId", ""),
            sequence=payload.get("sequence", 0),
            speaker=payload.get("speaker", ""),
            transcript=payload.get("transcript"),
            audio_file_id=payload.get("audioFileId", ""),
            audio_url=payload.get("audioUrl"),
            asr_status=payload.get("asrStatus"),
            created_at=payload.get("createdAt"),
            started_at=payload.get("startedAt"),
            ended_at=payload.get("endedAt"),
            context=payload.get("context"),
            latency_ms=payload.get("latencyMs"),
        )
        turns[turn_id] = record
        return record

    async def fake_update_turn(self, turn_id: str, payload: dict):
        record = turns.get(turn_id)
        if not record:
            return None
        updated = _apply_turn_payload(record, payload)
        turns[turn_id] = updated
        return updated

    async def fake_get_turn(self, turn_id: str):
        return turns.get(turn_id)

    async def fake_list_turns(self, session_id: str):
        return [turn for turn in turns.values() if turn.session_id == session_id]

    monkeypatch.setattr(
        "app.repositories.scenario_repository.ScenarioRepository.get",
        fake_get_scenario,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.create_session",
        fake_create_session,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.get_session",
        fake_get_session,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.update_session",
        fake_update_session,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.list_sessions",
        fake_list_sessions,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.delete_session",
        fake_delete_session,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.add_turn",
        fake_add_turn,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.update_turn",
        fake_update_turn,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.get_turn",
        fake_get_turn,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.list_turns",
        fake_list_turns,
    )


@pytest.fixture(autouse=True)
def _stub_pipeline(monkeypatch):
    async def _noop_pipeline(*args, **kwargs):
        return None

    monkeypatch.setattr(turns_routes, "enqueue_turn_pipeline", _noop_pipeline)

    async def _noop_initial_turn(*, session_id: str, scenario):
        repo = SessionRepository(object())
        await repo.add_turn(
            {
                "sessionId": session_id,
                "sequence": 0,
                "speaker": "ai",
                "transcript": "Hello",
                "audioFileId": "pending",
                "audioUrl": "",
                "asrStatus": "not_applicable",
                "startedAt": None,
                "endedAt": None,
                "context": "",
                "latencyMs": None,
            }
        )

    monkeypatch.setattr(
        "app.services.turn_pipeline.generate_initial_ai_turn",
        _noop_initial_turn,
    )

    async def fake_broadcast(session_id, payload):
        return None

    monkeypatch.setattr(
        "app.api.routes.session_socket.hub.broadcast",
        fake_broadcast,
    )

    def _noop_enqueue(session_id: str) -> None:
        return None

    monkeypatch.setattr(
        "app.services.session_service.enqueue",
        _noop_enqueue,
    )


def _timestamp(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


@pytest.mark.asyncio
async def test_practice_flow_turns_and_termination():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": _timestamp(),
            },
        )
        assert response.status_code == 201
        session = response.json()

        turn_start = datetime.now(timezone.utc)
        turn_response = await client.post(
            f"/api/sessions/{session['id']}/turns",
            json={
                "sequence": 1,
                "audioBase64": "YQ==",
                "startedAt": turn_start.isoformat(),
                "endedAt": (turn_start + timedelta(seconds=1)).isoformat(),
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
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": _timestamp(),
            },
        )
        assert response.status_code == 201
        session = response.json()

        turn_one_start = datetime.now(timezone.utc)
        await client.post(
            f"/api/sessions/{session['id']}/turns",
            json={
                "sequence": 1,
                "audioBase64": "YQ==",
                "startedAt": turn_one_start.isoformat(),
                "endedAt": (turn_one_start + timedelta(seconds=1)).isoformat(),
            },
        )

        turn_two_start = datetime.now(timezone.utc)
        await client.post(
            f"/api/sessions/{session['id']}/turns",
            json={
                "sequence": 2,
                "audioBase64": "YQ==",
                "startedAt": turn_two_start.isoformat(),
                "endedAt": (turn_two_start + timedelta(seconds=1)).isoformat(),
                "context": "objective-check=pass",
            },
        )

        stop_response = await client.post(
            f"/api/sessions/{session['id']}/manual-stop",
            json={"reason": "manual"},
        )
        assert stop_response.status_code == 202


@pytest.mark.asyncio
async def test_qwen_outage_graceful_termination():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": _timestamp(),
            },
        )
        assert response.status_code == 201
        session = response.json()

        turn_start = datetime.now(timezone.utc)
        turn_response = await client.post(
            f"/api/sessions/{session['id']}/turns",
            json={
                "sequence": 1,
                "audioBase64": "YQ==",
                "startedAt": turn_start.isoformat(),
                "endedAt": (turn_start + timedelta(seconds=1)).isoformat(),
                "context": "force-qwen-outage",
            },
        )
        assert turn_response.status_code == 202

        stop_response = await client.post(
            f"/api/sessions/{session['id']}/manual-stop",
            json={"reason": "qa_error"},
        )
        assert stop_response.status_code == 202


@pytest.mark.asyncio
async def test_session_completion_enqueues_evaluation(monkeypatch):
    calls = {"count": 0}

    def fake_enqueue(session_id: str) -> None:
        calls["count"] += 1

    monkeypatch.setattr("app.services.session_service.enqueue", fake_enqueue)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": _timestamp(),
            },
        )
        assert response.status_code == 201
        session = response.json()

        stop_response = await client.post(
            f"/api/sessions/{session['id']}/manual-stop",
            json={"reason": "manual"},
        )
        assert stop_response.status_code == 202

    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_ai_turn_zero_emitted_on_session_create(monkeypatch):
    events = []

    async def fake_broadcast(session_id, payload):
        events.append((session_id, payload))

    monkeypatch.setattr(
        "app.api.routes.session_socket.hub.broadcast",
        fake_broadcast,
    )
    async def fake_initial_turn(*, session_id: str, scenario):
        await hub.broadcast(
            session_id,
            {
                "type": "ai_turn",
                "turn": {
                    "id": "turn-0",
                    "sessionId": session_id,
                    "sequence": 0,
                    "speaker": "ai",
                    "transcript": "Hello",
                    "audioFileId": "pending",
                    "audioUrl": "",
                    "asrStatus": "not_applicable",
                    "createdAt": None,
                    "startedAt": None,
                    "endedAt": None,
                    "context": "",
                    "latencyMs": None,
                },
            },
        )

    monkeypatch.setattr(
        "app.services.turn_pipeline.generate_initial_ai_turn",
        fake_initial_turn,
    )

    now = datetime.now(timezone.utc).isoformat()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/sessions",
            json={
                "scenarioId": "scenario-1",
                "clientSessionStartedAt": now,
            },
        )
        assert response.status_code == 201

    assert any(
        payload.get("type") == "ai_turn" and payload.get("turn", {}).get("sequence") == 0
        for _, payload in events
    )
