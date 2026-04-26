from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest

from app.api.routes import callbacks as callbacks_routes
from app.api.routes import evaluations as evaluations_routes
from app.api.routes import history as history_routes
from app.api.routes import sessions as sessions_routes
from app.main import app
from app.models.evaluation import EvaluationResult, EvaluationScore
from app.repositories.evaluation_repository import EvaluationRecord
from app.repositories.session_repository import PracticeSessionRecord, TurnRecord
from app.services import session_service
from app.tasks import evaluation_runner


def _signature(secret: str, payload: dict[str, Any]) -> tuple[bytes, str]:
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return body, signature


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
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
    monkeypatch.setenv("ADMIN_ACCESS_TOKEN", "token")
    monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", "test-callback-secret")


@pytest.fixture(autouse=True)
def _reset_session_service_state(monkeypatch):
    session_service._FINALIZE_LOCKS.clear()
    session_service._PENDING_EVALUATION_TASKS.clear()
    session_service._EVALUATION_ENQUEUED.clear()
    monkeypatch.setattr(session_service, "_REALTIME_EVALUATION_GRACE_SECONDS", 0.0)


@pytest.mark.asyncio
async def test_realtime_session_history_and_evaluation_use_existing_turn_contract(monkeypatch):
    sessions: dict[str, PracticeSessionRecord] = {}
    turns: dict[str, TurnRecord] = {}
    evaluation: EvaluationRecord | None = None
    session_counter = 0
    turn_counter = 0
    captured_context: Any | None = None
    enqueue_calls: list[str] = []

    scenario = SimpleNamespace(
        id="scenario-1",
        metadata={
            "title": "Discuss a delayed launch",
            "domain": "Feedback",
            "scenarioType": "Coaching",
        },
        context={
            "situation": "A teammate needs to revisit a slipping timeline.",
            "background": "The project has missed two milestones.",
            "setting": "A short internal phone call.",
        },
        simulation_config={
            "ai": {"name": "Jordan", "role": "Manager"},
            "trainee": {"name": "Alex", "role": "IC"},
            "conversationStart": {
                "speakerRoleId": "trainee",
                "initialPromptToUser": "Explain the timeline risk.",
            },
        },
        evaluation_config={
            "learningObjectives": ["Name the risk clearly"],
            "evaluationCriteria": [
                {
                    "id": "clear_request",
                    "description": "States the timeline issue clearly",
                }
            ],
            "skillsAssessed": ["clear_request"],
            "scoring": {"scale": "1-5"},
            "evaluationInstructionsForLLM": "Use the existing criteria ids.",
        },
        status="published",
    )

    def _apply_session_payload(
        record: PracticeSessionRecord, payload: dict[str, Any]
    ) -> PracticeSessionRecord:
        data = {
            "id": record.id,
            "scenario_id": record.scenario_id,
            "stub_user_id": record.stub_user_id,
            "user_id": record.user_id,
            "language": record.language,
            "opening_prompt": record.opening_prompt,
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
            "mode": record.mode,
            "rtc_room_id": record.rtc_room_id,
            "rtc_task_id": record.rtc_task_id,
            "realtime_state": record.realtime_state,
        }
        mapping = {
            "scenarioId": "scenario_id",
            "stubUserId": "stub_user_id",
            "userId": "user_id",
            "language": "language",
            "openingPrompt": "opening_prompt",
            "status": "status",
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
            "mode": "mode",
            "rtcRoomId": "rtc_room_id",
            "rtcTaskId": "rtc_task_id",
            "realtimeState": "realtime_state",
        }
        for key, value in payload.items():
            field = mapping.get(key)
            if field:
                data[field] = value
        return PracticeSessionRecord(**data)

    def _apply_turn_payload(record: TurnRecord, payload: dict[str, Any]) -> TurnRecord:
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
            "is_interrupted": record.is_interrupted,
            "interrupted_at_ms": record.interrupted_at_ms,
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
            "isInterrupted": "is_interrupted",
            "interruptedAtMs": "interrupted_at_ms",
        }
        for key, value in payload.items():
            field = mapping.get(key)
            if field:
                data[field] = value
        return TurnRecord(**data)

    class FakeSessionRepo:
        async def create_session(self, payload: dict[str, Any]):
            nonlocal session_counter
            session_counter += 1
            session_id = f"session-{session_counter}"
            record = PracticeSessionRecord(
                id=session_id,
                scenario_id=str(payload.get("scenarioId", "")),
                stub_user_id=str(payload.get("stubUserId", "")),
                user_id=cast(str | None, payload.get("userId")),
                language=cast(str | None, payload.get("language")),
                opening_prompt=cast(str | None, payload.get("openingPrompt")),
                status=str(payload.get("status", "pending")),
                client_session_started_at=str(payload.get("clientSessionStartedAt", "")),
                started_at=cast(str | None, payload.get("startedAt")),
                ended_at=cast(str | None, payload.get("endedAt")),
                total_duration_seconds=cast(int | None, payload.get("totalDurationSeconds")),
                idle_limit_seconds=cast(int | None, payload.get("idleLimitSeconds")),
                duration_limit_seconds=cast(int | None, payload.get("durationLimitSeconds")),
                ws_channel=str(payload.get("wsChannel", "")),
                objective_status=str(payload.get("objectiveStatus", "unknown")),
                objective_reason=cast(str | None, payload.get("objectiveReason")),
                termination_reason=cast(str | None, payload.get("terminationReason")),
                evaluation_id=cast(str | None, payload.get("evaluationId")),
                mode=cast(Any, payload.get("mode", "turn_based")),
                rtc_room_id=cast(str | None, payload.get("rtcRoomId")),
                rtc_task_id=cast(str | None, payload.get("rtcTaskId")),
                realtime_state=cast(Any, payload.get("realtimeState")),
            )
            sessions[session_id] = record
            return record

        async def get_session(self, session_id: str):
            return sessions.get(session_id)

        async def update_session(self, session_id: str, payload: dict[str, Any]):
            record = sessions.get(session_id)
            if not record:
                return None
            updated = _apply_session_payload(record, payload)
            sessions[session_id] = updated
            return updated

        async def list_sessions(self, stub_user_id=None, user_id=None):
            items = list(sessions.values())
            if stub_user_id:
                items = [item for item in items if item.stub_user_id == stub_user_id]
            if user_id:
                items = [item for item in items if item.user_id == user_id]
            return items

        async def add_turn(self, payload: dict[str, Any]):
            nonlocal turn_counter
            turn_counter += 1
            turn_id = f"turn-{turn_counter}"
            record = TurnRecord(
                id=turn_id,
                session_id=str(payload.get("sessionId", "")),
                sequence=int(payload.get("sequence", 0)),
                speaker=str(payload.get("speaker", "")),
                transcript=cast(str | None, payload.get("transcript")),
                audio_file_id=str(payload.get("audioFileId", "")),
                audio_url=cast(str | None, payload.get("audioUrl")),
                asr_status=cast(str | None, payload.get("asrStatus")),
                created_at=cast(str | None, payload.get("createdAt")),
                started_at=cast(str | None, payload.get("startedAt")),
                ended_at=cast(str | None, payload.get("endedAt")),
                context=cast(str | None, payload.get("context")),
                latency_ms=cast(int | None, payload.get("latencyMs")),
                is_interrupted=bool(payload.get("isInterrupted", False)),
                interrupted_at_ms=cast(int | None, payload.get("interruptedAtMs")),
            )
            turns[turn_id] = record
            return record

        async def update_turn(self, turn_id: str, payload: dict[str, Any]):
            record = turns.get(turn_id)
            if not record:
                return None
            updated = _apply_turn_payload(record, payload)
            turns[turn_id] = updated
            return updated

        async def list_turns(self, session_id: str):
            return [turn for turn in turns.values() if turn.session_id == session_id]

        async def get_session_by_rtc_task_id(self, rtc_task_id: str):
            for session in sessions.values():
                if session.rtc_task_id == rtc_task_id:
                    return session
            return None

        async def get_session_by_rtc_room_id(self, rtc_room_id: str):
            for session in sessions.values():
                if session.rtc_room_id == rtc_room_id:
                    return session
            return None

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return scenario if scenario_id == scenario.id else None

    class FakeEvaluationRepo:
        async def create_evaluation(self, payload: dict[str, Any]):
            nonlocal evaluation
            evaluation = EvaluationRecord(
                id="eval-1",
                session_id=str(payload["sessionId"]),
                status=str(payload["status"]),
                scores=cast(list[dict[str, Any]], payload.get("scores", [])),
                summary=cast(str | None, payload.get("summary")),
                evaluator_model=str(payload.get("evaluatorModel", "gpt-5-mini")),
                attempts=int(payload.get("attempts", 1)),
                last_error=cast(str | None, payload.get("lastError")),
                queued_at=cast(str | None, payload.get("queuedAt")),
                completed_at=cast(str | None, payload.get("completedAt")),
            )
            return evaluation

        async def update_evaluation(self, evaluation_id: str, payload: dict[str, Any]):
            nonlocal evaluation
            assert evaluation is not None
            evaluation = EvaluationRecord(
                id=evaluation_id,
                session_id=evaluation.session_id,
                status=str(payload.get("status", evaluation.status)),
                scores=cast(list[dict[str, Any]], payload.get("scores", evaluation.scores)),
                summary=cast(str | None, payload.get("summary", evaluation.summary)),
                evaluator_model=evaluation.evaluator_model,
                attempts=int(payload.get("attempts", evaluation.attempts)),
                last_error=cast(str | None, payload.get("lastError", evaluation.last_error)),
                queued_at=cast(str | None, payload.get("queuedAt", evaluation.queued_at)),
                completed_at=cast(str | None, payload.get("completedAt", evaluation.completed_at)),
            )
            return evaluation

        async def get_by_session(self, session_id: str):
            if evaluation and evaluation.session_id == session_id:
                return evaluation
            return None

    class FakeSigningClient:
        async def get_signed_url(self, url, expires=900):
            return f"{url}?signed=1"

    @dataclass
    class RepoBundle:
        session_repo: object
        scenario_repo: object
        evaluation_repo: object
        mongodb_client: object

    class FakeClient:
        async def close(self):
            return None

    session_repo = FakeSessionRepo()
    scenario_repo = FakeScenarioRepo()
    evaluation_repo = FakeEvaluationRepo()

    async def _build_repositories():
        return RepoBundle(
            session_repo=session_repo,
            scenario_repo=scenario_repo,
            evaluation_repo=evaluation_repo,
            mongodb_client=FakeClient(),
        )

    async def fake_evaluate_session(context):
        nonlocal captured_context
        captured_context = context
        return EvaluationResult(
            scores=[
                EvaluationScore(
                    skill_id="clear_request",
                    rating=4,
                    note="Clear description of the risk.",
                )
            ],
            summary="The trainee clearly named the timeline issue.",
        )

    async def _broadcast(*_args, **_kwargs):
        return None

    monkeypatch.setattr(session_service, "enqueue", lambda session_id: enqueue_calls.append(session_id))
    monkeypatch.setattr(evaluation_runner, "_build_repositories", _build_repositories)
    monkeypatch.setattr(evaluation_runner, "evaluate_session", fake_evaluate_session)
    monkeypatch.setattr(
        evaluation_runner, "hub", type("Hub", (), {"broadcast": _broadcast})()
    )

    app.dependency_overrides[sessions_routes._repo] = lambda: session_repo
    app.dependency_overrides[sessions_routes._scenario_repo] = lambda: scenario_repo
    app.dependency_overrides[callbacks_routes._repo] = lambda: session_repo
    app.dependency_overrides[history_routes._session_repo] = lambda: session_repo
    app.dependency_overrides[history_routes._scenario_repo] = lambda: scenario_repo
    app.dependency_overrides[history_routes._evaluation_repo] = lambda: evaluation_repo
    app.dependency_overrides[history_routes._signing_client] = lambda: FakeSigningClient()
    app.dependency_overrides[evaluations_routes._session_repo] = lambda: session_repo
    app.dependency_overrides[evaluations_routes._evaluation_repo] = lambda: evaluation_repo

    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post(
                "/api/sessions",
                json={
                    "scenarioId": scenario.id,
                    "clientSessionStartedAt": datetime.now(timezone.utc).isoformat(),
                },
            )
            assert create_response.status_code == 201
            session_id = create_response.json()["id"]

            ai_body, ai_signature = _signature(
                "test-callback-secret",
                {
                    "event": "transcript_update",
                    "sessionId": session_id,
                    "aiTranscript": "Thanks for joining the call.",
                    "RoundID": 0,
                },
            )
            ai_response = await client.post(
                "/api/callbacks/doubao",
                content=ai_body,
                headers={"Content-Type": "application/json", "X-Signature": ai_signature},
            )
            assert ai_response.status_code == 202
            assert ai_response.json()["turnsCreated"] == 1

            trainee_body, trainee_signature = _signature(
                "test-callback-secret",
                {
                    "event": "transcript_update",
                    "sessionId": session_id,
                    "userTranscript": "I want to revisit the launch timeline.",
                    "RoundID": 0,
                },
            )
            trainee_response = await client.post(
                "/api/callbacks/doubao",
                content=trainee_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature": trainee_signature,
                },
            )
            assert trainee_response.status_code == 202
            assert trainee_response.json()["turnsCreated"] == 1

            end_body, end_signature = _signature(
                "test-callback-secret",
                {
                    "event": "conversation_end",
                    "sessionId": session_id,
                    "RunStage": "taskStop",
                },
            )
            end_response = await client.post(
                "/api/callbacks/doubao",
                content=end_body,
                headers={"Content-Type": "application/json", "X-Signature": end_signature},
            )
            assert end_response.status_code == 202
            assert end_response.json()["processed"] is True

            await evaluation_runner._run_evaluation(session_id)

            history_response = await client.get(
                f"/api/sessions/{session_id}", params={"historyStepCount": 2}
            )
            evaluation_response = await client.get(f"/api/sessions/{session_id}/evaluation")

        assert enqueue_calls == [session_id]
        assert captured_context is not None
        assert [turn["speaker"] for turn in captured_context.turns] == ["trainee", "ai"]
        assert [turn["transcript"] for turn in captured_context.turns] == [
            "I want to revisit the launch timeline.",
            "Thanks for joining the call.",
        ]

        assert history_response.status_code == 200
        history_payload = cast(dict[str, Any], history_response.json())
        assert history_payload["session"]["mode"] == "realtime"
        assert history_payload["session"]["status"] == "ended"
        assert history_payload["session"]["evaluationId"] == "eval-1"
        assert [turn["speaker"] for turn in history_payload["turns"]] == ["trainee", "ai"]
        assert [turn["transcript"] for turn in history_payload["turns"]] == [
            "I want to revisit the launch timeline.",
            "Thanks for joining the call.",
        ]
        assert history_payload["turns"][0]["audioUrl"] is None
        assert history_payload["turns"][1]["audioUrl"] is None
        assert history_payload["evaluation"]["sessionId"] == session_id
        assert history_payload["evaluation"]["status"] == "completed"
        assert history_payload["evaluation"]["scores"][0]["skillId"] == "clear_request"

        assert evaluation_response.status_code == 200
        evaluation_payload = cast(dict[str, Any], evaluation_response.json())
        assert evaluation_payload["sessionId"] == session_id
        assert evaluation_payload["status"] == "completed"
        assert evaluation_payload["scores"][0]["skillId"] == "clear_request"
    finally:
        app.dependency_overrides.pop(sessions_routes._repo, None)
        app.dependency_overrides.pop(sessions_routes._scenario_repo, None)
        app.dependency_overrides.pop(callbacks_routes._repo, None)
        app.dependency_overrides.pop(history_routes._session_repo, None)
        app.dependency_overrides.pop(history_routes._scenario_repo, None)
        app.dependency_overrides.pop(history_routes._evaluation_repo, None)
        app.dependency_overrides.pop(history_routes._signing_client, None)
        app.dependency_overrides.pop(evaluations_routes._session_repo, None)
        app.dependency_overrides.pop(evaluations_routes._evaluation_repo, None)
