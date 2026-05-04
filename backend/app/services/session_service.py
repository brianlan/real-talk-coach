from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.repositories.session_repository import PracticeSessionRecord, SessionRepository
from app.tasks.evaluation_runner import enqueue, set_tracking_clearer
from app.telemetry.tracing import emit_metric
from app.config import load_settings

logger = logging.getLogger(__name__)

_FINALIZE_LOCKS: dict[str, asyncio.Lock] = {}
_PENDING_EVALUATION_TASKS: dict[str, asyncio.Task[None]] = {}
_EVALUATION_ENQUEUED: set[str] = set()
_REALTIME_EVALUATION_GRACE_SECONDS = 1.0


class CapacityError(Exception):
    pass


def _is_terminal(status: str) -> bool:
    return status == "ended"


def _session_lock(session_id: str) -> asyncio.Lock:
    lock = _FINALIZE_LOCKS.get(session_id)
    if lock is None:
        lock = asyncio.Lock()
        _FINALIZE_LOCKS[session_id] = lock
    return lock


def _clear_evaluation_tracking(session_id: str) -> None:
    _EVALUATION_ENQUEUED.discard(session_id)
    pending = _PENDING_EVALUATION_TASKS.get(session_id)
    if pending is not None and pending.done():
        _PENDING_EVALUATION_TASKS.pop(session_id, None)


set_tracking_clearer(_clear_evaluation_tracking)


async def _enqueue_after_grace(session_id: str, delay_seconds: float) -> None:
    try:
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        async with _session_lock(session_id):
            if session_id in _EVALUATION_ENQUEUED:
                return
            _EVALUATION_ENQUEUED.add(session_id)
        enqueue(session_id)
    finally:
        _PENDING_EVALUATION_TASKS.pop(session_id, None)


async def _maybe_enqueue_terminal_evaluation(
    repo: SessionRepository,
    session: PracticeSessionRecord,
) -> None:
    if not _is_terminal(session.status):
        return
    if session.evaluation_id or session.id in _EVALUATION_ENQUEUED:
        return

    turns = await repo.list_turns(session.id)
    if turns:
        pending = _PENDING_EVALUATION_TASKS.pop(session.id, None)
        if pending is not None:
            pending.cancel()
        _EVALUATION_ENQUEUED.add(session.id)
        enqueue(session.id)
        return

    if session.mode != "realtime":
        _EVALUATION_ENQUEUED.add(session.id)
        enqueue(session.id)
        return

    pending = _PENDING_EVALUATION_TASKS.get(session.id)
    if pending is not None and not pending.done():
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _EVALUATION_ENQUEUED.add(session.id)
        enqueue(session.id)
        return

    _PENDING_EVALUATION_TASKS[session.id] = loop.create_task(
        _enqueue_after_grace(session.id, _REALTIME_EVALUATION_GRACE_SECONDS)
    )


async def ensure_capacity(
    repo: SessionRepository,
    *,
    user_id: str | None = None,
    max_active: int = 20,
    max_pending: int = 5,
) -> None:
    settings = load_settings()
    try:
        sessions = await repo.list_sessions(settings.stub_user_id, user_id)
    except TypeError:
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
) -> PracticeSessionRecord | None:
    return await finalize_session(
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
    *,
    realtime_source: bool = False,
) -> PracticeSessionRecord | None:
    async with _session_lock(session_id):
        existing = await repo.get_session(session_id)
        if not existing:
            return None

        was_terminal = _is_terminal(existing.status)
        update_payload = dict(payload)
        target_status = update_payload.get("status", existing.status)
        terminal_after_update = _is_terminal(target_status)

        if existing.mode == "realtime" and terminal_after_update:
            update_payload.setdefault("realtimeState", "ended")

        if was_terminal:
            if existing.termination_reason:
                update_payload["terminationReason"] = existing.termination_reason
            elif payload.get("terminationReason") in (None, ""):
                update_payload.pop("terminationReason", None)
            if existing.ended_at:
                update_payload["endedAt"] = existing.ended_at
            elif payload.get("endedAt") in (None, ""):
                update_payload.pop("endedAt", None)

        session = await repo.update_session(session_id, update_payload)
        if not session:
            return None

        # For realtime sessions, only the e2e socket path triggers evaluation.
        # manual_stop and callback paths skip it to avoid races with
        # in-flight transcript persistence.
        if session.mode == "realtime" and not realtime_source:
            return session

        await _maybe_enqueue_terminal_evaluation(repo, session)

        return session


async def initiate_session(
    repo: SessionRepository,
    session_id: str,
    *,
    scenario: Any,
    language: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    session = await repo.update_session(
        session_id,
        {
            "status": "active",
            "startedAt": now,
        },
    )
    if not session:
        logger.error("[%s] Failed to update session status", session_id)
        return
    logger.info(
        "[%s] Practice session startup completed without legacy turn pipeline (mode=%s)",
        session_id,
        session.mode,
    )
