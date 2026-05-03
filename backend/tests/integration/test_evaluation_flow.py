"""Red-phase integration test for the evaluation flow.

This test encodes the expectation that evaluation uses
evaluationConfig from the nested scenario (not skill_summaries)
and that scores reference evaluationCriteria[].id.  It is expected
to FAIL until the production code is refactored.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.repositories.evaluation_repository import EvaluationRecord
from app.repositories.session_repository import PracticeSessionRecord, TurnRecord
from app.services import session_service
from app.tasks import evaluation_runner


def _make_nested_scenario():
    """Return a namespace-like object with the canonical nested shape."""
    from types import SimpleNamespace

    return SimpleNamespace(
        id="scenario-1",
        metadata={
            "title": "Request a Salary Increase",
            "slug": "salary-raise",
            "domain": "Workplace",
            "scenarioType": "Negotiation",
        },
        context={
            "situation": "Employee wants a raise.",
            "background": "Budget is tight.",
            "setting": "1-on-1 meeting.",
        },
        simulationConfig={
            "ai": {
                "name": "Jordan",
                "role": "Engineering Manager",
                "personality": ["professional"],
                "motivations": ["retain talent"],
                "constraints": ["budget is tight"],
                "tendencies": ["cautious"],
                "knowledge": ["employee took on more work"],
                "emotionalState": "calm",
            },
            "trainee": {
                "name": "Alex",
                "role": "Software Engineer",
                "personality": ["professional"],
                "motivations": ["fair pay"],
                "constraints": ["avoid confrontation"],
                "tendencies": ["prepared"],
                "knowledge": ["market research done"],
                "emotionalState": "motivated",
            },
            "language": "English",
            "conversationStart": {
                "speakerRoleId": "employee",
                "initialPromptToUser": "Start the conversation.",
            },
            "conversationRules": {
                "stayInCharacter": True,
                "allowNarration": False,
                "coachingAllowed": False,
                "tone": "professional",
            },
            "conversationDynamics": {
                "typicalBehaviors": ["ask for examples"],
                "possibleResponses": ["mention fairness"],
            },
            "decisionConstraints": {
                "maxRaiseWithoutHigherApprovalPercent": 8,
                "alternativeOptions": ["bonus"],
            },
            "conversationEndConditions": {
                "possibleEndStates": ["raise approved"],
            },
        },
        evaluationConfig={
            "learningObjectives": [
                "make a clear compensation request",
                "support the request with evidence",
            ],
            "evaluationCriteria": [
                {
                    "id": "responsibility_articulation",
                    "description": "Explains expanded responsibilities clearly",
                },
                {
                    "id": "clear_request",
                    "description": "Makes a direct compensation request",
                },
            ],
            "skillsAssessed": [
                "clear_request",
                "negotiation",
                "evidence_based_persuasion",
            ],
            "scoring": {
                "scale": "1-5",
                "criteriaWeighting": {
                    "responsibility_articulation": 0.5,
                    "clear_request": 0.5,
                },
            },
            "evaluationInstructionsForLLM": (
                "Evaluate the trainee's performance."
            ),
        },
    )


@pytest.mark.asyncio
async def test_evaluation_uses_evaluation_config_not_skill_summaries(monkeypatch):
    """The evaluation runner must read evaluationConfig from the scenario,
    not skill_summaries, and scores must use evaluationCriteria[].id values."""
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

    session_id = "session-1"
    session_record = PracticeSessionRecord(
        id=session_id,
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        language="en",
        opening_prompt="Hello",
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
            transcript="Hi, I'd like to discuss my compensation.",
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
        mongodb_client: object

    class FakeSessionRepo:
        async def get_session(self, sid: str):
            return session_record if sid == session_record.id else None

        async def update_session(self, sid: str, payload: dict):
            nonlocal session_record
            session_record = PracticeSessionRecord(
                id=session_record.id,
                scenario_id=session_record.scenario_id,
                stub_user_id=session_record.stub_user_id,
                language=session_record.language,
                opening_prompt=session_record.opening_prompt,
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

        async def list_turns(self, sid: str):
            return turns

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return _make_nested_scenario()

    evaluation_record: EvaluationRecord | None = None
    captured_context = None

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

        async def get_by_session(self, sid: str):
            return evaluation_record

    class FakeClient:
        async def close(self):
            return None
        async def db(self):
            return {}
        async def collection(self, name):
            return {}

    async def _build_repositories():
        return RepoBundle(
            session_repo=FakeSessionRepo(),
            scenario_repo=FakeScenarioRepo(),
            evaluation_repo=FakeEvaluationRepo(),
            mongodb_client=FakeClient(),
        )

    async def fake_evaluate_session(_context):
        nonlocal captured_context
        captured_context = _context
        from app.models.evaluation import EvaluationResult, EvaluationScore

        return EvaluationResult(
            scores=[
                EvaluationScore(
                    skill_id="responsibility_articulation", rating=4, note="Good"
                ),
                EvaluationScore(
                    skill_id="clear_request", rating=5, note="Very clear"
                ),
            ],
            summary="Nice work",
        )

    async def _broadcast(*_args, **_kwargs):
        return None

    monkeypatch.setattr(evaluation_runner, "_build_repositories", _build_repositories)
    monkeypatch.setattr(evaluation_runner, "evaluate_session", fake_evaluate_session)
    monkeypatch.setattr(
        evaluation_runner, "hub", type("Hub", (), {"broadcast": _broadcast})()
    )

    await evaluation_runner._run_evaluation(session_id)

    assert evaluation_record is not None
    assert evaluation_record.status == "completed"
    assert evaluation_record.summary == "Nice work"
    assert captured_context is not None
    assert captured_context.scenario_title == "Request a Salary Increase"
    assert captured_context.learning_objectives == [
        "make a clear compensation request",
        "support the request with evidence",
    ]
    assert [item["id"] for item in captured_context.evaluation_criteria] == [
        "responsibility_articulation",
        "clear_request",
    ]
    assert captured_context.skills_assessed == [
        "clear_request",
        "negotiation",
        "evidence_based_persuasion",
    ]
    assert captured_context.evaluation_instructions == "Evaluate the trainee's performance."

    score_ids = [score["skillId"] for score in evaluation_record.scores]
    assert "responsibility_articulation" in score_ids
    assert "clear_request" in score_ids

    # Legacy skill IDs must NOT appear in scores
    assert "skill-1" not in score_ids


@pytest.mark.asyncio
async def test_evaluation_retries_until_success(monkeypatch):
    """Evaluation must retry on failure and ultimately succeed with criteria IDs."""
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

    session_id = "session-1"
    session_record = PracticeSessionRecord(
        id=session_id,
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        language="en",
        opening_prompt="Hello",
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
        mongodb_client: object

    class FakeSessionRepo:
        async def get_session(self, sid: str):
            return session_record if sid == session_record.id else None

        async def update_session(self, sid: str, payload: dict):
            nonlocal session_record
            session_record = PracticeSessionRecord(
                id=session_record.id,
                scenario_id=session_record.scenario_id,
                stub_user_id=session_record.stub_user_id,
                language=session_record.language,
                opening_prompt=session_record.opening_prompt,
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

        async def list_turns(self, sid: str):
            return turns

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return _make_nested_scenario()

    evaluation_record: EvaluationRecord | None = None
    captured_contexts = []

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

        async def get_by_session(self, sid: str):
            return evaluation_record

    class FakeClient:
        async def close(self):
            return None
        async def db(self):
            return {}
        async def collection(self, name):
            return {}

    async def _build_repositories():
        return RepoBundle(
            session_repo=FakeSessionRepo(),
            scenario_repo=FakeScenarioRepo(),
            evaluation_repo=FakeEvaluationRepo(),
            mongodb_client=FakeClient(),
        )

    calls = {"count": 0}

    async def fake_evaluate_session(_context):
        captured_contexts.append(_context)
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("temporary failure")
        from app.models.evaluation import EvaluationResult, EvaluationScore

        return EvaluationResult(
            scores=[
                EvaluationScore(
                    skill_id="responsibility_articulation", rating=4, note="Good"
                ),
                EvaluationScore(
                    skill_id="clear_request", rating=5, note="Clear"
                ),
            ],
            summary="Nice work",
        )

    async def _broadcast(*_args, **_kwargs):
        return None

    monkeypatch.setattr(evaluation_runner, "_build_repositories", _build_repositories)
    monkeypatch.setattr(evaluation_runner, "evaluate_session", fake_evaluate_session)
    monkeypatch.setattr(
        evaluation_runner, "hub", type("Hub", (), {"broadcast": _broadcast})()
    )

    await evaluation_runner._run_evaluation(session_id)

    assert evaluation_record is not None
    assert evaluation_record.status == "completed"
    assert evaluation_record.attempts == 2
    assert evaluation_record.summary == "Nice work"
    assert captured_contexts
    assert [item["id"] for item in captured_contexts[0].evaluation_criteria] == [
        "responsibility_articulation",
        "clear_request",
    ]

    score_ids = [score["skillId"] for score in evaluation_record.scores]
    assert "responsibility_articulation" in score_ids
    assert "clear_request" in score_ids
    assert "skill-1" not in score_ids


@pytest.mark.asyncio
async def test_evaluation_fails_with_zero_turns(monkeypatch):
    """An ended session with zero persisted turns must fail immediately
    with an explicit error, not produce a misleading score."""
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

    session_id = "session-empty"
    session_record = PracticeSessionRecord(
        id=session_id,
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        language="en",
        opening_prompt=None,
        status="ended",
        client_session_started_at="2025-01-01T00:00:00Z",
        started_at="2025-01-01T00:00:00Z",
        ended_at="2025-01-01T00:05:00Z",
        total_duration_seconds=300,
        idle_limit_seconds=8,
        duration_limit_seconds=300,
        ws_channel=f"/ws/sessions/{session_id}",
        objective_status="unknown",
        objective_reason=None,
        termination_reason="idle_timeout",
        evaluation_id=None,
        mode="realtime",
    )

    @dataclass
    class RepoBundle:
        session_repo: object
        scenario_repo: object
        evaluation_repo: object
        mongodb_client: object

    class FakeSessionRepo:
        async def get_session(self, sid: str):
            return session_record if sid == session_record.id else None

        async def update_session(self, sid: str, payload: dict):
            nonlocal session_record
            session_record = PracticeSessionRecord(
                id=session_record.id,
                scenario_id=session_record.scenario_id,
                stub_user_id=session_record.stub_user_id,
                language=session_record.language,
                opening_prompt=session_record.opening_prompt,
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
                mode=session_record.mode,
            )
            return session_record

        async def list_turns(self, sid: str):
            return []

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return _make_nested_scenario()

    evaluation_record: EvaluationRecord | None = None

    class FakeEvaluationRepo:
        async def create_evaluation(self, payload: dict):
            nonlocal evaluation_record
            evaluation_record = EvaluationRecord(
                id="eval-empty-1",
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

        async def get_by_session(self, sid: str):
            return evaluation_record

    class FakeClient:
        async def close(self):
            return None
        async def db(self):
            return {}
        async def collection(self, name):
            return {}

    async def _build_repositories():
        return RepoBundle(
            session_repo=FakeSessionRepo(),
            scenario_repo=FakeScenarioRepo(),
            evaluation_repo=FakeEvaluationRepo(),
            mongodb_client=FakeClient(),
        )

    async def _broadcast(*_args, **_kwargs):
        return None

    monkeypatch.setattr(evaluation_runner, "_build_repositories", _build_repositories)
    monkeypatch.setattr(
        evaluation_runner, "hub", type("Hub", (), {"broadcast": _broadcast})()
    )

    await evaluation_runner._run_evaluation(session_id)

    assert evaluation_record is not None
    assert evaluation_record.status == "failed"
    assert evaluation_record.last_error is not None
    assert "no persisted turns" in evaluation_record.last_error.lower()
    assert evaluation_record.scores == []
    assert evaluation_record.summary is None


@pytest.mark.asyncio
async def test_evaluation_succeeds_with_turns_after_guardrail(monkeypatch):
    """Sessions with persisted turns must still evaluate and broadcast normally."""
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

    session_id = "session-with-turns"
    session_record = PracticeSessionRecord(
        id=session_id,
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        language="en",
        opening_prompt="Hello",
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
            id="turn-a",
            session_id=session_id,
            sequence=0,
            speaker="ai",
            transcript="Hello, how can I help?",
            audio_file_id="file-a",
            audio_url=None,
            asr_status=None,
            created_at=None,
            started_at=None,
            ended_at=None,
            context=None,
            latency_ms=None,
        ),
        TurnRecord(
            id="turn-b",
            session_id=session_id,
            sequence=1,
            speaker="trainee",
            transcript="I'd like a raise.",
            audio_file_id="file-b",
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
        mongodb_client: object

    class FakeSessionRepo:
        async def get_session(self, sid: str):
            return session_record if sid == session_record.id else None

        async def update_session(self, sid: str, payload: dict):
            nonlocal session_record
            session_record = PracticeSessionRecord(
                id=session_record.id,
                scenario_id=session_record.scenario_id,
                stub_user_id=session_record.stub_user_id,
                language=session_record.language,
                opening_prompt=session_record.opening_prompt,
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

        async def list_turns(self, sid: str):
            return turns

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return _make_nested_scenario()

    evaluation_record: EvaluationRecord | None = None

    class FakeEvaluationRepo:
        async def create_evaluation(self, payload: dict):
            nonlocal evaluation_record
            evaluation_record = EvaluationRecord(
                id="eval-ok-1",
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

        async def get_by_session(self, sid: str):
            return evaluation_record

    class FakeClient:
        async def close(self):
            return None
        async def db(self):
            return {}
        async def collection(self, name):
            return {}

    async def _build_repositories():
        return RepoBundle(
            session_repo=FakeSessionRepo(),
            scenario_repo=FakeScenarioRepo(),
            evaluation_repo=FakeEvaluationRepo(),
            mongodb_client=FakeClient(),
        )

    async def fake_evaluate_session(_context):
        from app.models.evaluation import EvaluationResult, EvaluationScore

        return EvaluationResult(
            scores=[
                EvaluationScore(skill_id="clear_request", rating=4, note="ok"),
            ],
            summary="Good",
        )

    broadcast_called = {"called": False}

    async def _broadcast(*_args, **_kwargs):
        broadcast_called["called"] = True

    monkeypatch.setattr(evaluation_runner, "_build_repositories", _build_repositories)
    monkeypatch.setattr(evaluation_runner, "evaluate_session", fake_evaluate_session)
    monkeypatch.setattr(
        evaluation_runner, "hub", type("Hub", (), {"broadcast": _broadcast})()
    )

    await evaluation_runner._run_evaluation(session_id)

    assert evaluation_record is not None
    assert evaluation_record.status == "completed"
    assert evaluation_record.summary == "Good"
    assert len(evaluation_record.scores) == 1
    assert evaluation_record.scores[0]["skillId"] == "clear_request"
    assert broadcast_called["called"] is True


@pytest.mark.asyncio
async def test_evaluation_run_clears_enqueue_tracking_after_completion(monkeypatch):
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

    session_service._EVALUATION_ENQUEUED.clear()
    session_id = "session-cleanup"
    session_service._EVALUATION_ENQUEUED.add(session_id)

    session_record = PracticeSessionRecord(
        id=session_id,
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        language="en",
        opening_prompt="Hello",
        status="ended",
        client_session_started_at="2025-01-01T00:00:00Z",
        started_at="2025-01-01T00:00:00Z",
        ended_at="2025-01-01T00:05:00Z",
        total_duration_seconds=300,
        idle_limit_seconds=8,
        duration_limit_seconds=300,
        ws_channel=f"/ws/sessions/{session_id}",
        objective_status="unknown",
        objective_reason=None,
        termination_reason="manual",
        evaluation_id=None,
        mode="realtime",
    )
    turns = [
        TurnRecord(
            id="turn-cleanup-1",
            session_id=session_id,
            sequence=0,
            speaker="trainee",
            transcript="Let's talk about the delay.",
            audio_file_id="file-1",
            audio_url=None,
            asr_status="completed",
            created_at=None,
            started_at=None,
            ended_at=None,
            context=None,
            latency_ms=None,
        )
    ]

    @dataclass
    class RepoBundle:
        session_repo: object
        scenario_repo: object
        evaluation_repo: object
        mongodb_client: object

    class FakeSessionRepo:
        async def get_session(self, sid: str):
            return session_record if sid == session_record.id else None

        async def update_session(self, sid: str, payload: dict):
            nonlocal session_record
            session_record = PracticeSessionRecord(
                id=session_record.id,
                scenario_id=session_record.scenario_id,
                stub_user_id=session_record.stub_user_id,
                language=session_record.language,
                opening_prompt=session_record.opening_prompt,
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
                mode=session_record.mode,
            )
            return session_record

        async def list_turns(self, sid: str):
            return turns

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return _make_nested_scenario()

    evaluation_record: EvaluationRecord | None = None

    class FakeEvaluationRepo:
        async def create_evaluation(self, payload: dict):
            nonlocal evaluation_record
            evaluation_record = EvaluationRecord(
                id="eval-cleanup-1",
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

        async def get_by_session(self, sid: str):
            return evaluation_record

    class FakeClient:
        async def close(self):
            return None

        async def db(self):
            return {}

        async def collection(self, name):
            return {}

    async def _build_repositories():
        return RepoBundle(
            session_repo=FakeSessionRepo(),
            scenario_repo=FakeScenarioRepo(),
            evaluation_repo=FakeEvaluationRepo(),
            mongodb_client=FakeClient(),
        )

    async def fake_evaluate_session(_context):
        from app.models.evaluation import EvaluationResult, EvaluationScore

        return EvaluationResult(
            scores=[EvaluationScore(skill_id="clear_request", rating=4, note="ok")],
            summary="Good",
        )

    async def _broadcast(*_args, **_kwargs):
        return None

    monkeypatch.setattr(evaluation_runner, "_build_repositories", _build_repositories)
    monkeypatch.setattr(evaluation_runner, "evaluate_session", fake_evaluate_session)
    monkeypatch.setattr(
        evaluation_runner, "hub", type("Hub", (), {"broadcast": _broadcast})()
    )

    await evaluation_runner._run_evaluation(session_id)

    assert session_id not in session_service._EVALUATION_ENQUEUED


@pytest.mark.asyncio
async def test_late_transcript_failed_realtime_evaluation_can_recover(monkeypatch):
    from app.api.routes import callbacks as callbacks_routes

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

    session_id = "session-late-turns"
    session_record = PracticeSessionRecord(
        id=session_id,
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        language="en",
        opening_prompt=None,
        status="ended",
        client_session_started_at="2025-01-01T00:00:00Z",
        started_at="2025-01-01T00:00:00Z",
        ended_at="2025-01-01T00:05:00Z",
        total_duration_seconds=300,
        idle_limit_seconds=8,
        duration_limit_seconds=300,
        ws_channel=f"/ws/sessions/{session_id}",
        objective_status="unknown",
        objective_reason=None,
        termination_reason="idle_timeout",
        evaluation_id=None,
        mode="realtime",
    )
    turns: list[TurnRecord] = []
    enqueue_calls: list[str] = []

    @dataclass
    class RepoBundle:
        session_repo: object
        scenario_repo: object
        evaluation_repo: object
        mongodb_client: object

    class FakeSessionRepo:
        async def get_session(self, sid: str):
            return session_record if sid == session_record.id else None

        async def update_session(self, sid: str, payload: dict):
            nonlocal session_record
            session_record = PracticeSessionRecord(
                id=session_record.id,
                scenario_id=session_record.scenario_id,
                stub_user_id=session_record.stub_user_id,
                language=session_record.language,
                opening_prompt=session_record.opening_prompt,
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
                mode=session_record.mode,
            )
            return session_record

        async def list_turns(self, sid: str):
            return list(turns)

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return _make_nested_scenario()

    evaluation_record: EvaluationRecord | None = None

    class FakeEvaluationRepo:
        async def create_evaluation(self, payload: dict):
            nonlocal evaluation_record
            evaluation_record = EvaluationRecord(
                id="eval-late-1",
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

        async def get_by_session(self, sid: str):
            return evaluation_record

    class FakeClient:
        async def close(self):
            return None

        async def db(self):
            return {}

        async def collection(self, name):
            return {}

    async def _build_repositories():
        return RepoBundle(
            session_repo=FakeSessionRepo(),
            scenario_repo=FakeScenarioRepo(),
            evaluation_repo=FakeEvaluationRepo(),
            mongodb_client=FakeClient(),
        )

    async def fake_evaluate_session(_context):
        from app.models.evaluation import EvaluationResult, EvaluationScore

        return EvaluationResult(
            scores=[EvaluationScore(skill_id="clear_request", rating=5, note="Recovered")],
            summary="Recovered after transcript arrived",
        )

    async def _broadcast(*_args, **_kwargs):
        return None

    monkeypatch.setattr(evaluation_runner, "_build_repositories", _build_repositories)
    monkeypatch.setattr(evaluation_runner, "evaluate_session", fake_evaluate_session)
    monkeypatch.setattr(
        evaluation_runner, "hub", type("Hub", (), {"broadcast": _broadcast})()
    )
    monkeypatch.setattr(callbacks_routes, "enqueue", lambda sid: enqueue_calls.append(sid))

    await evaluation_runner._run_evaluation(session_id)

    assert evaluation_record is not None
    assert evaluation_record.status == "failed"
    assert evaluation_record.last_error is not None
    assert "no persisted turns" in evaluation_record.last_error.lower()

    turns.append(
        TurnRecord(
            id="turn-late-1",
            session_id=session_id,
            sequence=0,
            speaker="trainee",
            transcript="Here is the late transcript.",
            audio_file_id="file-late-1",
            audio_url=None,
            asr_status="completed",
            created_at=None,
            started_at=None,
            ended_at=None,
            context=None,
            latency_ms=None,
        )
    )

    recovered = await callbacks_routes._recover_failed_realtime_evaluation_if_needed(
        session_id,
        FakeSessionRepo(),
        FakeEvaluationRepo(),
        persisted_turns=1,
    )

    assert recovered is True
    assert enqueue_calls == [session_id]

    await evaluation_runner._run_evaluation(session_id)

    assert evaluation_record.status == "completed"
    assert evaluation_record.summary == "Recovered after transcript arrived"
    assert evaluation_record.attempts == 4
    assert evaluation_record.last_error is None
    assert evaluation_record.scores[0]["skillId"] == "clear_request"
