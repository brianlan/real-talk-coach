from __future__ import annotations

from typing import Any

from app.api.routes.session_socket import hub
from app.repositories.session_repository import SessionRepository
from app.tasks.evaluation_runner import enqueue
from app.telemetry.tracing import emit_metric
from app.config import load_settings


class CapacityError(Exception):
    pass


def _is_terminal(status: str) -> bool:
    return status == "ended"


async def ensure_capacity(
    repo: SessionRepository,
    *,
    max_active: int = 20,
    max_pending: int = 5,
) -> None:
    settings = load_settings()
    sessions = await repo.list_sessions(settings.stub_user_id)
    active = [session for session in sessions if session.status != "ended"]
    pending = [session for session in sessions if session.status == "pending"]
    if len(active) >= max_active or len(pending) >= max_pending:
        emit_metric(
            "pilot.capacity_exceeded",
            1,
            attributes={"active": len(active), "pending": len(pending)},
        )
        raise CapacityError("pilot capacity exceeded")


async def terminate_session(
    repo: SessionRepository,
    session_id: str,
    reason: str,
    ended_at: str,
) -> None:
    await finalize_session(
        repo,
        session_id,
        {
            "status": "ended",
            "terminationReason": reason,
            "endedAt": ended_at,
        },
    )


async def finalize_session(
    repo: SessionRepository,
    session_id: str,
    payload: dict[str, Any],
) -> None:
    session = await repo.update_session(session_id, payload)
    if not session:
        return
    if session.termination_reason:
        await repo.update_session(
            session_id,
            {
                "terminationReason": session.termination_reason,
                "endedAt": session.ended_at,
            },
        )
    if _is_terminal(session.status):
        enqueue(session_id)


async def initiate_session(
    repo: SessionRepository,
    session_id: str,
    *,
    transcript: str,
) -> None:
    session = await repo.update_session(
        session_id,
        {
            "status": "active",
            "startedAt": session_id,  # placeholder; will be overwritten by backend timestamps
        },
    )
    if not session:
        return
    ai_turn = await repo.add_turn(
        {
            "sessionId": session_id,
            "sequence": 0,
            "speaker": "ai",
            "transcript": transcript,
            "audioFileId": "pending",
            "audioUrl": None,
            "asrStatus": None,
            "createdAt": session.started_at,
            "startedAt": session.started_at,
            "endedAt": session.started_at,
            "context": None,
            "latencyMs": None,
        }
    )
    await hub.broadcast(
        session_id,
        {
            "type": "ai_turn",
            "turn": {
                "id": ai_turn.id,
                "sessionId": ai_turn.session_id,
                "sequence": ai_turn.sequence,
                "speaker": ai_turn.speaker,
                "transcript": ai_turn.transcript,
                "audioFileId": ai_turn.audio_file_id,
                "audioUrl": ai_turn.audio_url,
                "asrStatus": ai_turn.asr_status,
                "createdAt": ai_turn.created_at,
                "startedAt": ai_turn.started_at,
                "endedAt": ai_turn.ended_at,
                "context": ai_turn.context,
                "latencyMs": ai_turn.latency_ms,
            },
        },
    )
