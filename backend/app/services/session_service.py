from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.repositories.session_repository import SessionRepository
from app.tasks.evaluation_runner import enqueue
from app.telemetry.tracing import emit_metric
from app.config import load_settings

logger = logging.getLogger(__name__)


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
    scenario: Any,
    language: str,
) -> None:
    print(f"[{session_id}] ===== initiate_session called =====")  # DEBUG
    logger.info(f"[{session_id}] initiate_session called")
    now = datetime.now(timezone.utc).isoformat()
    session = await repo.update_session(
        session_id,
        {
            "status": "active",
            "startedAt": now,
        },
    )
    if not session:
        logger.error(f"[{session_id}] Failed to update session status")
        return
    opening_prompt = None
    opening_prompt_model = None
    opening_prompt_provider = None
    opening_prompt_created_at = None
    try:
        from app.services.opening_prompt_service import generate_opening_prompt

        opening_prompt, opening_prompt_model, opening_prompt_provider, opening_prompt_created_at = (
            await generate_opening_prompt(scenario=scenario, language=language)
        )
    except Exception as exc:
        logger.warning(
            "[%s] Opening prompt generation failed; falling back to default. Error: %s",
            session_id,
            exc,
        )

    if opening_prompt:
        await repo.update_session(
            session_id,
            {
                "openingPrompt": {
                    "text": opening_prompt,
                    "language": language,
                    "model": opening_prompt_model,
                    "provider": opening_prompt_provider,
                    "createdAt": opening_prompt_created_at,
                },
            },
        )
    from app.services.turn_pipeline import generate_initial_ai_turn

    print(f"[{session_id}] About to call generate_initial_ai_turn")  # DEBUG
    logger.info(f"[{session_id}] About to call generate_initial_ai_turn")
    await generate_initial_ai_turn(
        session_id=session_id,
        scenario=scenario,
        opening_prompt=opening_prompt,
        language=language,
    )
    print(f"[{session_id}] generate_initial_ai_turn completed")  # DEBUG
    logger.info(f"[{session_id}] generate_initial_ai_turn completed")
