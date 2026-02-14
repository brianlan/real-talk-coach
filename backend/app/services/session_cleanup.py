from __future__ import annotations

import logging

from bson import ObjectId

from app.clients.minio import MinioClient
from app.clients.mongodb import MongoDBClient
from app.config import load_settings
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


async def cleanup_session(session_id: str) -> None:
    settings = load_settings()
    mongo_connection_string = f"mongodb://{settings.mongo_host}:{settings.mongo_port}"
    client = MongoDBClient(
        connection_string=mongo_connection_string,
        database=settings.mongo_db,
    )
    minio_client = MinioClient(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
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
                    await minio_client.delete_file(turn.audio_file_id)
                except Exception as exc:
                    logger.warning(
                        "Failed to delete audio file %s: %s", turn.audio_file_id, exc
                    )
            try:
                turns_collection = await client.collection("Turn")
                await turns_collection.delete_one({"_id": ObjectId(turn.id)})
            except Exception as exc:
                logger.warning("Failed to delete turn %s: %s", turn.id, exc)
        evaluation = await evaluation_repo.get_by_session(session_id)
        if evaluation:
            try:
                eval_collection = await client.collection("Evaluation")
                await eval_collection.delete_one({"_id": ObjectId(evaluation.id)})
            except Exception as exc:
                logger.warning("Failed to delete evaluation %s: %s", evaluation.id, exc)
        await session_repo.delete_session(session_id)
    finally:
        await client.close()
