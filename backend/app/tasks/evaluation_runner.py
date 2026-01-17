from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.api.routes.session_socket import hub
from app.clients.leancloud import LeanCloudClient
from app.config import load_settings
from app.repositories.evaluation_repository import EvaluationRecord, EvaluationRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.session_repository import SessionRepository
from app.services.evaluation_service import EvaluationContext, evaluate_session
from app.telemetry.otel import start_span
from app.telemetry.tracing import emit_metric

logger = logging.getLogger(__name__)

_IN_FLIGHT: set[str] = set()
_LOCK = asyncio.Lock()


@dataclass(frozen=True)
class _Repos:
    session_repo: SessionRepository
    scenario_repo: ScenarioRepository
    evaluation_repo: EvaluationRepository
    leancloud_client: LeanCloudClient


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _build_repositories() -> _Repos:
    settings = load_settings()
    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    return _Repos(
        session_repo=SessionRepository(client),
        scenario_repo=ScenarioRepository(client),
        evaluation_repo=EvaluationRepository(client),
        leancloud_client=client,
    )


def enqueue(session_id: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("No running event loop; evaluation enqueue skipped")
        return
    loop.create_task(_run_evaluation(session_id))


async def _run_evaluation(session_id: str) -> None:
    async with _LOCK:
        if session_id in _IN_FLIGHT:
            return
        _IN_FLIGHT.add(session_id)
    try:
        repos = await _build_repositories()
        try:
            await _evaluate_with_retries(session_id, repos)
        finally:
            await repos.leancloud_client.close()
    finally:
        async with _LOCK:
            _IN_FLIGHT.discard(session_id)


async def _evaluate_with_retries(session_id: str, repos: _Repos) -> None:
    session = await repos.session_repo.get_session(session_id)
    if not session:
        return
    evaluation = await repos.evaluation_repo.get_by_session(session_id)
    if evaluation and evaluation.status == "running":
        return
    if evaluation and evaluation.status == "completed":
        return
    if evaluation and evaluation.status == "failed":
        return

    if not evaluation:
        with start_span(
            "evaluation.store",
            {"sessionId": session_id, "operation": "create"},
        ):
            evaluation = await repos.evaluation_repo.create_evaluation(
                {
                    "sessionId": session_id,
                    "status": "pending",
                    "scores": [],
                    "summary": None,
                    "evaluatorModel": load_settings().evaluator_model,
                    "attempts": 1,
                    "lastError": None,
                    "queuedAt": _utc_now(),
                    "completedAt": None,
                }
            )
        with start_span(
            "evaluation.store",
            {"sessionId": session_id, "operation": "link_session"},
        ):
            await repos.session_repo.update_session(
                session_id, {"evaluationId": evaluation.id}
            )

    await _run_attempts(session_id, repos, evaluation)


async def _run_attempts(
    session_id: str,
    repos: _Repos,
    evaluation: EvaluationRecord,
) -> None:
    backoff_seconds = [0.4, 0.8]
    attempts_remaining = len(backoff_seconds) + 1
    for attempt_index in range(attempts_remaining):
        attempt_number = evaluation.attempts + attempt_index
        with start_span(
            "evaluation.run",
            {"sessionId": session_id, "attempt": attempt_number, "status": "running"},
        ):
            with start_span(
                "evaluation.store",
                {
                    "sessionId": session_id,
                    "operation": "status_update",
                    "status": "running",
                },
            ):
                await repos.evaluation_repo.update_evaluation(
                    evaluation.id,
                    {
                        "status": "running",
                        "attempts": attempt_number,
                        "lastError": None,
                    },
                )
            try:
                result = await _evaluate_once(session_id, repos)
                record = await _mark_completed(
                    repos,
                    evaluation.id,
                    result,
                    session_id=session_id,
                    attempts=attempt_number,
                )
                await _emit_queue_latency_metric(
                    session_id,
                    (record.queued_at if record else evaluation.queued_at),
                    (record.completed_at if record else datetime.now(timezone.utc).isoformat()),
                )
                await hub.broadcast(
                    session_id,
                    {
                        "type": "evaluation_ready",
                        "evaluation": _evaluation_response(
                            session_id,
                            result,
                            evaluator_model=load_settings().evaluator_model,
                            record=record,
                        ),
                    },
                )
                return
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                body = getattr(exc, "body", None)
                message = str(exc)
                with start_span(
                    "evaluation.store",
                    {
                        "sessionId": session_id,
                        "operation": "error_update",
                        "status": "running",
                    },
                ):
                    await repos.evaluation_repo.update_evaluation(
                        evaluation.id, {"lastError": message}
                    )
                logger.warning(
                    "Evaluation attempt failed session_id=%s attempt=%s error=%s status=%s body=%s",
                    session_id,
                    attempt_number,
                    message,
                    status_code,
                    body,
                )
                if attempt_index < len(backoff_seconds):
                    await asyncio.sleep(backoff_seconds[attempt_index])
                    continue
                with start_span(
                    "evaluation.store",
                    {
                        "sessionId": session_id,
                        "operation": "status_update",
                        "status": "failed",
                    },
                ):
                    await repos.evaluation_repo.update_evaluation(
                        evaluation.id,
                        {
                            "status": "failed",
                            "completedAt": _utc_now(),
                            "lastError": message,
                            "attempts": attempt_number,
                        },
                    )
                return


async def _evaluate_once(session_id: str, repos: _Repos):
    session = await repos.session_repo.get_session(session_id)
    if not session:
        raise ValueError("session missing")
    scenario = await repos.scenario_repo.get(session.scenario_id)
    if not scenario:
        raise ValueError("scenario missing")
    turns = await repos.session_repo.list_turns(session_id)
    context = EvaluationContext(
        session_id=session_id,
        scenario_title=scenario.title,
        objective=scenario.objective,
        skill_summaries=scenario.skill_summaries,
        turns=[
            {"speaker": turn.speaker, "transcript": turn.transcript}
            for turn in turns
        ],
    )
    with start_span(
        "evaluation.llm",
        {"sessionId": session_id, "status": "request"},
    ):
        return await evaluate_session(context)


async def _mark_completed(
    repos: _Repos,
    evaluation_id: str,
    result,
    *,
    session_id: str,
    attempts: int,
) -> EvaluationRecord | None:
    scores_payload = [
        {"skillId": score.skill_id, "rating": score.rating, "note": score.note}
        for score in result.scores
    ]
    with start_span(
        "evaluation.store",
        {"sessionId": session_id, "operation": "status_update", "status": "completed"},
    ):
        return await repos.evaluation_repo.update_evaluation(
            evaluation_id,
            {
                "status": "completed",
                "scores": scores_payload,
                "summary": result.summary,
                "completedAt": _utc_now(),
                "attempts": attempts,
            },
        )


async def _emit_queue_latency_metric(
    session_id: str,
    queued_at: str | None,
    completed_at: str | None,
) -> None:
    if not queued_at or not completed_at:
        return
    try:
        queued = datetime.fromisoformat(queued_at)
        completed = datetime.fromisoformat(completed_at)
    except ValueError:
        return
    latency = (completed - queued).total_seconds()
    with start_span(
        "evaluation.queue_latency",
        {"sessionId": session_id, "status": "completed", "latency": latency},
    ):
        emit_metric(
            "evaluation.queue_latency",
            latency,
            session_id=session_id,
            attributes={"status": "completed"},
        )


def _evaluation_response(
    session_id: str,
    result: Any,
    *,
    evaluator_model: str,
    record: EvaluationRecord | None,
) -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "status": "completed",
        "scores": [
            {"skillId": score.skill_id, "rating": score.rating, "note": score.note}
            for score in result.scores
        ],
        "summary": result.summary,
        "evaluatorModel": evaluator_model,
        "attempts": record.attempts if record else None,
        "lastError": record.last_error if record else None,
        "queuedAt": record.queued_at if record else None,
        "completedAt": record.completed_at if record else _utc_now(),
    }
