from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from app.models.evaluation import EvaluationResult, EvaluationScore
from app.repositories.evaluation_repository import EvaluationRecord
from app.repositories.session_repository import PracticeSessionRecord, TurnRecord
from app.services import evaluation_service
from app.tasks import evaluation_runner


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


@pytest.mark.asyncio
async def test_queue_latency_span_includes_latency(monkeypatch):
    spans = []

    def fake_start_span(name, attributes=None):
        spans.append((name, attributes))
        class Dummy:
            def __enter__(self_inner):
                return None
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return Dummy()

    monkeypatch.setattr(evaluation_runner, "start_span", fake_start_span)
    monkeypatch.setattr(evaluation_runner, "emit_metric", lambda *args, **kwargs: None)

    queued_at = datetime.now(timezone.utc).isoformat()
    completed_at = datetime.now(timezone.utc).isoformat()
    await evaluation_runner._emit_queue_latency_metric("session-1", queued_at, completed_at)

    assert spans
    assert spans[0][0] == "evaluation.queue_latency"
    assert "latency" in spans[0][1]


@pytest.mark.asyncio
async def test_evaluation_runner_store_spans_include_session_id(monkeypatch):
    _set_env(monkeypatch)
    spans = []

    def fake_start_span(name, attributes=None):
        spans.append((name, attributes))
        class Dummy:
            def __enter__(self_inner):
                return None
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return Dummy()

    monkeypatch.setattr(evaluation_runner, "start_span", fake_start_span)

    session = PracticeSessionRecord(
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
    evaluation = EvaluationRecord(
        id="eval-1",
        session_id="session-1",
        status="pending",
        scores=[],
        summary=None,
        evaluator_model="gpt-5-mini",
        attempts=1,
        last_error=None,
        queued_at="2025-01-01T00:00:00+00:00",
        completed_at=None,
    )

    class FakeSessionRepo:
        async def get_session(self, session_id: str):
            return session

        async def list_turns(self, session_id: str):
            return [
                TurnRecord(
                    id="turn-1",
                    session_id="session-1",
                    sequence=0,
                    speaker="ai",
                    transcript="Hi",
                    audio_file_id="file-1",
                    audio_url=None,
                    asr_status=None,
                    created_at=None,
                    started_at=None,
                    ended_at=None,
                    context=None,
                    latency_ms=None,
                )
            ]

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return type(
                "Scenario",
                (),
                {
                    "title": "Scenario",
                    "objective": "Objective",
                    "skill_summaries": [],
                },
            )()

    class FakeEvaluationRepo:
        async def update_evaluation(self, evaluation_id: str, payload: dict):
            return evaluation

    @dataclass
    class FakeRepos:
        session_repo: FakeSessionRepo
        scenario_repo: FakeScenarioRepo
        evaluation_repo: FakeEvaluationRepo
        leancloud_client: object

    async def _broadcast(*_args, **_kwargs):
        return None

    async def _fake_evaluate_once(*_args, **_kwargs):
        return EvaluationResult(
            scores=[EvaluationScore(skill_id="skill-1", rating=4, note="ok")],
            summary="ok",
        )

    monkeypatch.setattr(evaluation_runner, "_evaluate_once", _fake_evaluate_once)
    monkeypatch.setattr(evaluation_runner, "hub", type("Hub", (), {"broadcast": _broadcast})())
    monkeypatch.setattr(evaluation_runner, "emit_metric", lambda *args, **kwargs: None)

    await evaluation_runner._run_attempts(
        "session-1",
        FakeRepos(
            session_repo=FakeSessionRepo(),
            scenario_repo=FakeScenarioRepo(),
            evaluation_repo=FakeEvaluationRepo(),
            leancloud_client=object(),
        ),
        evaluation,
    )

    assert any(name == "evaluation.store" and attrs.get("sessionId") == "session-1" for name, attrs in spans if attrs)


@pytest.mark.asyncio
async def test_evaluation_service_spans_include_session_id(monkeypatch):
    spans = []

    def fake_start_span(name, attributes=None):
        spans.append((name, attributes))
        class Dummy:
            def __enter__(self_inner):
                return None
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return Dummy()

    class FakeClient:
        async def evaluate(self, payload):
            return {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "arguments": (
                                            '{"scores":[{"skillId":"skill-1","rating":4,"note":"ok"}],"summary":"nice"}'
                                        )
                                    }
                                }
                            ]
                        }
                    }
                ]
            }

        async def close(self):
            return None

    monkeypatch.setattr(evaluation_service, "start_span", fake_start_span)
    monkeypatch.setattr(evaluation_service, "EvaluatorClient", lambda *args, **kwargs: FakeClient())
    _set_env(monkeypatch)

    context = evaluation_service.EvaluationContext(
        session_id="session-1",
        scenario_title="Scenario",
        objective="Objective",
        skill_summaries=[{"skillId": "skill-1", "name": "Skill", "rubric": "Rubric"}],
        turns=[{"speaker": "ai", "transcript": "Hi"}],
    )
    result = await evaluation_service.evaluate_session(context)

    assert result.summary == "nice"
    assert any(attrs.get("sessionId") == "session-1" for _, attrs in spans if attrs)
