from __future__ import annotations

import logging

from app.clients.leancloud import LeanCloudClient
from app.config import load_settings
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


async def cleanup_session(session_id: str) -> None:
    settings = load_settings()
    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    session_repo = SessionRepository(client)
    evaluation_repo = EvaluationRepository(client)
    try:
        session = await session_repo.get_session(session_id)
        if not session:
            return
        turns = await session_repo.list_turns(session_id)
        for turn in turns:
            if turn.audio_file_id:
                try:
                    await client.delete_json(f"/1.1/files/{turn.audio_file_id}")
                except Exception as exc:
                    logger.warning(
                        "Failed to delete audio file %s: %s", turn.audio_file_id, exc
                    )
            try:
                await client.delete_json(f"/1.1/classes/Turn/{turn.id}")
            except Exception as exc:
                logger.warning("Failed to delete turn %s: %s", turn.id, exc)
        evaluation = await evaluation_repo.get_by_session(session_id)
        if evaluation:
            try:
                await client.delete_json(f"/1.1/classes/Evaluation/{evaluation.id}")
            except Exception as exc:
                logger.warning("Failed to delete evaluation %s: %s", evaluation.id, exc)
        await session_repo.delete_session(session_id)
    finally:
        await client.close()
