from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.repositories.evaluation_repository import EvaluationRecord
from app.repositories.scenario_repository import Scenario
from app.repositories.session_repository import PracticeSessionRecord, TurnRecord
from app.tasks import evaluation_runner


@pytest.mark.asyncio
async def test_evaluation_retries_until_success(monkeypatch):
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
    session_id = "session-1"
    session_record = PracticeSessionRecord(
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
        evaluation_id=None,
    )
    turns = [
        TurnRecord(
            id="turn-1",
            session_id=session_id,
            sequence=0,
            speaker="ai",
            transcript="Hello",
            audio_file_id="file-1",
            audio_url=None,
            asr_status=None,
            created_at=None,
            started_at=None,
            ended_at=None,
            context=None,
            latency_ms=None,
        ),
        TurnRecord(
            id="turn-2",
            session_id=session_id,
            sequence=1,
            speaker="trainee",
            transcript="Hi",
            audio_file_id="file-2",
            audio_url=None,
            asr_status="completed",
            created_at=None,
            started_at=None,
            ended_at=None,
            context=None,
            latency_ms=None,
        ),
    ]

    @dataclass
    class RepoBundle:
        session_repo: object
        scenario_repo: object
        evaluation_repo: object
        leancloud_client: object

    class FakeSessionRepo:
        async def get_session(self, session_id: str):
            return session_record if session_id == session_record.id else None

        async def update_session(self, session_id: str, payload: dict):
            nonlocal session_record
            session_record = PracticeSessionRecord(
                id=session_record.id,
                scenario_id=session_record.scenario_id,
                stub_user_id=session_record.stub_user_id,
                status=payload.get("status", session_record.status),
                client_session_started_at=session_record.client_session_started_at,
                started_at=session_record.started_at,
                ended_at=session_record.ended_at,
                total_duration_seconds=session_record.total_duration_seconds,
                idle_limit_seconds=session_record.idle_limit_seconds,
                duration_limit_seconds=session_record.duration_limit_seconds,
                ws_channel=session_record.ws_channel,
                objective_status=session_record.objective_status,
                objective_reason=session_record.objective_reason,
                termination_reason=session_record.termination_reason,
                evaluation_id=payload.get("evaluationId", session_record.evaluation_id),
            )
            return session_record

        async def list_turns(self, session_id: str):
            return turns

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return Scenario(
                id=scenario_id,
                category="practice",
                title="Scenario",
                description="desc",
                objective="Objective",
                ai_persona={"name": "AI"},
                trainee_persona={"name": "You"},
                end_criteria=["done"],
                skills=["skill-1"],
                skill_summaries=[
                    {"skillId": "skill-1", "name": "Skill", "rubric": "Rubric"}
                ],
                idle_limit_seconds=8,
                duration_limit_seconds=300,
                prompt="Prompt",
                status="published",
            )

    evaluation_record: EvaluationRecord | None = None

    class FakeEvaluationRepo:
        async def create_evaluation(self, payload: dict):
            nonlocal evaluation_record
            evaluation_record = EvaluationRecord(
                id="eval-1",
                session_id=payload["sessionId"],
                status=payload["status"],
                scores=payload.get("scores", []),
                summary=payload.get("summary"),
                evaluator_model=payload.get("evaluatorModel", "gpt-5-mini"),
                attempts=payload.get("attempts", 1),
                last_error=payload.get("lastError"),
                queued_at=payload.get("queuedAt"),
                completed_at=payload.get("completedAt"),
            )
            return evaluation_record

        async def update_evaluation(self, evaluation_id: str, payload: dict):
            nonlocal evaluation_record
            assert evaluation_record is not None
            evaluation_record = EvaluationRecord(
                id=evaluation_id,
                session_id=evaluation_record.session_id,
                status=payload.get("status", evaluation_record.status),
                scores=payload.get("scores", evaluation_record.scores),
                summary=payload.get("summary", evaluation_record.summary),
                evaluator_model=evaluation_record.evaluator_model,
                attempts=payload.get("attempts", evaluation_record.attempts),
                last_error=payload.get("lastError", evaluation_record.last_error),
                queued_at=payload.get("queuedAt", evaluation_record.queued_at),
                completed_at=payload.get("completedAt", evaluation_record.completed_at),
            )
            return evaluation_record

        async def get_by_session(self, session_id: str):
            return evaluation_record

    class FakeClient:
        async def close(self):
            return None

    async def _build_repositories():
        return RepoBundle(
            session_repo=FakeSessionRepo(),
            scenario_repo=FakeScenarioRepo(),
            evaluation_repo=FakeEvaluationRepo(),
            leancloud_client=FakeClient(),
        )

    calls = {"count": 0}

    async def fake_evaluate_session(_context):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("temporary failure")
        from app.models.evaluation import EvaluationResult, EvaluationScore

        return EvaluationResult(
            scores=[EvaluationScore(skill_id="skill-1", rating=4, note="Good")],
            summary="Nice work",
        )

    async def _broadcast(*_args, **_kwargs):
        return None

    monkeypatch.setattr(evaluation_runner, "_build_repositories", _build_repositories)
    monkeypatch.setattr(evaluation_runner, "evaluate_session", fake_evaluate_session)
    monkeypatch.setattr(evaluation_runner, "hub", type("Hub", (), {"broadcast": _broadcast})())

    await evaluation_runner._run_evaluation(session_id)

    assert evaluation_record is not None
    assert evaluation_record.status == "completed"
    assert evaluation_record.attempts == 2
    assert evaluation_record.summary == "Nice work"
