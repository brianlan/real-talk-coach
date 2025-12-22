from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.clients.leancloud import LeanCloudClient
from app.config import load_settings
from app.models.session import TurnInput
from app.repositories.session_repository import SessionRepository
from app.services.turn_pipeline import enqueue_turn_pipeline

router = APIRouter()

MAX_AUDIO_BYTES = 128 * 1024
MAX_AUDIO_BASE64_CHARS = 175000


def _repo() -> SessionRepository:
    settings = load_settings()
    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    return SessionRepository(client)


def _audio_size_bytes(audio_base64: str) -> int:
    if len(audio_base64) > MAX_AUDIO_BASE64_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio exceeds 128 KB; shorten or split the turn.",
        )
    try:
        return len(base64.b64decode(audio_base64, validate=True))
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid audio payload; please resend the turn.",
        ) from exc


@router.post("/sessions/{session_id}/turns", status_code=status.HTTP_202_ACCEPTED)
async def submit_turn(
    session_id: str,
    payload: TurnInput,
    repo: SessionRepository = Depends(_repo),
):
    size = _audio_size_bytes(payload.audioBase64)
    if size > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio exceeds 128 KB; shorten or split the turn.",
        )

    session = await repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if session.status == "ended":
        return {"sessionId": session_id, "turnId": "", "aiTurnId": None, "status": "closed"}

    existing_turns = await repo.list_turns(session_id)
    existing_sequences = {turn.sequence for turn in existing_turns}
    if payload.sequence in existing_sequences:
        return {
            "sessionId": session_id,
            "turnId": "",
            "aiTurnId": None,
            "status": "duplicate",
        }
    expected_sequence = max(existing_sequences, default=-1) + 1
    if payload.sequence != expected_sequence:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sequence; expected {expected_sequence}.",
        )

    record = await repo.add_turn(
        {
            "sessionId": session_id,
            "sequence": payload.sequence,
            "speaker": "trainee",
            "transcript": None,
            "audioFileId": "pending",
            "audioUrl": None,
            "asrStatus": "pending",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "startedAt": payload.startedAt.isoformat(),
            "endedAt": payload.endedAt.isoformat(),
            "context": payload.context,
            "latencyMs": None,
        }
    )
    await enqueue_turn_pipeline(
        session_id=session_id, turn_id=record.id, audio_base64=payload.audioBase64
    )

    return {
        "sessionId": session_id,
        "turnId": record.id,
        "aiTurnId": None,
        "status": "accepted",
    }
