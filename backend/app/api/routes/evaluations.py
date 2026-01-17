from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.clients.leancloud import LeanCloudClient
from app.config import load_settings
from app.repositories.evaluation_repository import EvaluationRecord, EvaluationRepository
from app.repositories.session_repository import SessionRepository
from app.tasks.evaluation_runner import enqueue
from app.telemetry.tracing import emit_metric

router = APIRouter()


def _evaluation_repo() -> EvaluationRepository:
    settings = load_settings()
    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    return EvaluationRepository(client)


def _session_repo() -> SessionRepository:
    settings = load_settings()
    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    return SessionRepository(client)


def _evaluation_response(record: EvaluationRecord) -> dict[str, object]:
    return {
        "sessionId": record.session_id,
        "status": record.status,
        "scores": record.scores,
        "summary": record.summary,
        "evaluatorModel": record.evaluator_model,
        "attempts": record.attempts,
        "lastError": record.last_error,
        "queuedAt": record.queued_at,
        "completedAt": record.completed_at,
    }


def _emit_latency_metric(record: EvaluationRecord) -> None:
    if not record.queued_at or not record.completed_at:
        return
    try:
        queued = datetime.fromisoformat(record.queued_at)
        completed = datetime.fromisoformat(record.completed_at)
    except ValueError:
        return
    latency = (completed - queued).total_seconds()
    emit_metric(
        "evaluation.queue_latency",
        latency,
        session_id=record.session_id,
        attributes={"status": record.status, "source": "api"},
    )


@router.get("/sessions/{session_id}/evaluation")
async def get_evaluation(
    session_id: str,
    session_repo: SessionRepository = Depends(_session_repo),
    evaluation_repo: EvaluationRepository = Depends(_evaluation_repo),
):
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    settings = load_settings()
    if session.stub_user_id != settings.stub_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    evaluation = await evaluation_repo.get_by_session(session_id)
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    _emit_latency_metric(evaluation)
    return _evaluation_response(evaluation)


@router.post("/sessions/{session_id}/evaluation", status_code=status.HTTP_202_ACCEPTED)
async def requeue_evaluation(
    session_id: str,
    session_repo: SessionRepository = Depends(_session_repo),
    evaluation_repo: EvaluationRepository = Depends(_evaluation_repo),
):
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    settings = load_settings()
    if session.stub_user_id != settings.stub_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    evaluation = await evaluation_repo.get_by_session(session_id)
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if evaluation.status != "failed":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_evaluation_response(evaluation),
        )
    queued_at = datetime.now(timezone.utc).isoformat()
    updated = await evaluation_repo.update_evaluation(
        evaluation.id,
        {
            "status": "pending",
            "attempts": evaluation.attempts + 1,
            "lastError": None,
            "queuedAt": queued_at,
            "completedAt": None,
        },
    )
    enqueue(session_id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    response = _evaluation_response(updated)
    if not response.get("sessionId"):
        response["sessionId"] = evaluation.session_id
    return response
