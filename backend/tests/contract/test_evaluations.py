"""Red-phase contract tests for evaluation endpoints.

These tests encode the expectation that evaluations use
evaluationConfig.evaluationCriteria[].id as score identifiers and
that evaluation context comes from the nested scenario schema.  They
are expected to FAIL until the production code is refactored.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import status

from app.main import app
from app.api.routes import evaluations as evaluations_routes
from app.repositories.evaluation_repository import EvaluationRecord
from app.repositories.session_repository import PracticeSessionRecord


EVALUATION_CRITERIA_IDS = [
    "responsibility_articulation",
    "evidence_support",
    "clear_request",
    "handling_pushback",
    "progress_toward_outcome",
]


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


@pytest.fixture(autouse=True)
def _override_repos(monkeypatch):
    evaluation = EvaluationRecord(
        id="eval-1",
        session_id="session-1",
        status="completed",
        scores=[
            {"skillId": "responsibility_articulation", "rating": 4, "note": "Good explanation"},
            {"skillId": "evidence_support", "rating": 3, "note": "Some evidence"},
            {"skillId": "clear_request", "rating": 5, "note": "Very clear"},
            {"skillId": "handling_pushback", "rating": 3, "note": "Handled okay"},
            {"skillId": "progress_toward_outcome", "rating": 4, "note": "Good progress"},
        ],
        summary="Solid performance overall.",
        evaluator_model="gpt-5-mini",
        attempts=1,
        last_error=None,
        queued_at="2025-01-01T00:00:00+00:00",
        completed_at="2025-01-01T00:00:10+00:00",
    )

    async def _get_session(session_id: str):
        return PracticeSessionRecord(
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
            evaluation_id="eval-1",
        )

    async def _get_by_session(session_id: str):
        return evaluation if session_id == evaluation.session_id else None

    async def _update_evaluation(evaluation_id: str, payload: dict):
        nonlocal evaluation
        evaluation = EvaluationRecord(
            id=evaluation_id,
            session_id=evaluation.session_id,
            status=payload.get("status", evaluation.status),
            scores=payload.get("scores", evaluation.scores),
            summary=payload.get("summary", evaluation.summary),
            evaluator_model=evaluation.evaluator_model,
            attempts=payload.get("attempts", evaluation.attempts),
            last_error=payload.get("lastError", evaluation.last_error),
            queued_at=payload.get("queuedAt", evaluation.queued_at),
            completed_at=payload.get("completedAt", evaluation.completed_at),
        )
        return evaluation

    class FakeSessionRepo:
        get_session = staticmethod(_get_session)

    class FakeEvaluationRepo:
        get_by_session = staticmethod(_get_by_session)
        update_evaluation = staticmethod(_update_evaluation)

    app.dependency_overrides[evaluations_routes._session_repo] = lambda: FakeSessionRepo()
    app.dependency_overrides[evaluations_routes._evaluation_repo] = lambda: FakeEvaluationRepo()
    monkeypatch.setattr(evaluations_routes, "enqueue", lambda *_args, **_kwargs: None)
    yield
    app.dependency_overrides.pop(evaluations_routes._session_repo, None)
    app.dependency_overrides.pop(evaluations_routes._evaluation_repo, None)


@pytest.mark.asyncio
async def test_get_evaluation_returns_criteria_id_scores():
    """Evaluation scores must use evaluationCriteria[].id as skillId values."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sessions/session-1/evaluation")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["sessionId"] == "session-1"
    assert payload["status"] == "completed"

    score_ids = [score["skillId"] for score in payload["scores"]]
    for criteria_id in EVALUATION_CRITERIA_IDS:
        assert criteria_id in score_ids, (
            f"Expected criteria id '{criteria_id}' in scores but got {score_ids}"
        )


@pytest.mark.asyncio
async def test_evaluation_scores_not_using_legacy_skill_ids():
    """Scores must use evaluation criteria IDs, not legacy Skill collection IDs."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sessions/session-1/evaluation")

    payload = response.json()
    score_ids = [score["skillId"] for score in payload["scores"]]

    # Legacy Skill IDs (like "skill-1") must NOT appear
    assert "skill-1" not in score_ids
    for sid in score_ids:
        assert sid in EVALUATION_CRITERIA_IDS


@pytest.mark.asyncio
async def test_requeue_evaluation_when_failed():
    # Create a fresh failed evaluation for this test
    failed_eval = EvaluationRecord(
        id="eval-failed-1",
        session_id="session-failed",
        status="failed",
        scores=[],
        summary=None,
        evaluator_model="gpt-5-mini",
        attempts=1,
        last_error="oops",
        queued_at="2025-01-01T00:00:00+00:00",
        completed_at="2025-01-01T00:00:10+00:00",
    )

    async def _get_failed(session_id: str):
        return failed_eval if session_id == failed_eval.session_id else None

    async def _update_failed(evaluation_id: str, payload: dict):
        return EvaluationRecord(
            id=evaluation_id,
            session_id=failed_eval.session_id,
            status=payload.get("status", "pending"),
            scores=payload.get("scores", []),
            summary=payload.get("summary"),
            evaluator_model=failed_eval.evaluator_model,
            attempts=payload.get("attempts", 2),
            last_error=payload.get("lastError"),
            queued_at=failed_eval.queued_at,
            completed_at=failed_eval.completed_at,
        )

    class FakeSessionRepo:
        async def get_session(self, sid):
            return PracticeSessionRecord(
                id=sid,
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
                ws_channel=f"/ws/sessions/{sid}",
                objective_status="unknown",
                objective_reason=None,
                termination_reason="manual",
                evaluation_id="eval-failed-1",
            )

    class FakeEvaluationRepo:
        get_by_session = staticmethod(_get_failed)
        update_evaluation = staticmethod(_update_failed)

    app.dependency_overrides[evaluations_routes._session_repo] = lambda: FakeSessionRepo()
    app.dependency_overrides[evaluations_routes._evaluation_repo] = lambda: FakeEvaluationRepo()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/session-failed/evaluation")

    assert response.status_code == status.HTTP_202_ACCEPTED
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["attempts"] == 2

    app.dependency_overrides.pop(evaluations_routes._session_repo, None)
    app.dependency_overrides.pop(evaluations_routes._evaluation_repo, None)


@pytest.mark.asyncio
async def test_requeue_evaluation_conflict():
    async def _get_by_session(session_id: str):
        return EvaluationRecord(
            id="eval-1",
            session_id=session_id,
            status="completed",
            scores=[
                {"skillId": "clear_request", "rating": 5, "note": "Perfect"},
            ],
            summary="ok",
            evaluator_model="gpt-5-mini",
            attempts=2,
            last_error=None,
            queued_at="2025-01-01T00:00:00+00:00",
            completed_at="2025-01-01T00:00:10+00:00",
        )

    class FakeEvaluationRepo:
        get_by_session = staticmethod(_get_by_session)
        update_evaluation = staticmethod(lambda *args, **kwargs: None)

    app.dependency_overrides[evaluations_routes._evaluation_repo] = lambda: FakeEvaluationRepo()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/session-1/evaluation")

    assert response.status_code == status.HTTP_409_CONFLICT
    payload = response.json()
    assert payload["status"] == "completed"
    app.dependency_overrides.pop(evaluations_routes._evaluation_repo, None)
