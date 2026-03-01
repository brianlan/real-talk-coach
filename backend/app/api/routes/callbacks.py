from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.clients.mongodb import MongoDBClient
from app.dependencies import get_mongodb_client
from app.repositories.session_repository import SessionRepository, TurnRecord

router = APIRouter()
logger = logging.getLogger(__name__)

_TRAINEE_SPEAKERS = {"user", "trainee", "human", "participant"}
_AI_SPEAKERS = {"ai", "assistant", "agent", "bot"}


class TranscriptItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    speaker: str | None = None
    transcript: str | None = None
    text: str | None = None
    sequence: int | None = Field(default=None, ge=0)
    turnId: str | None = None


class DoubaoCallbackPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    event: str | None = None
    event_type: str | None = None
    type: str | None = None
    EventType: int | None = None
    RunStage: str | None = None
    EventTime: int | None = None
    sessionId: str | None = None
    session_id: str | None = None
    taskId: str | None = None
    TaskId: str | None = None
    RoomId: str | None = None
    fromUserId: str | None = None
    subtitleText: str | None = None
    transcript: str | None = None
    text: str | None = None
    userTranscript: str | None = None
    aiTranscript: str | None = None
    RoundID: int | None = Field(default=None, ge=0)
    interrupt: bool | None = None
    turnId: str | None = None
    signature: str | None = None
    transcripts: list[TranscriptItem] = Field(default_factory=list)


def _repo(mongodb: MongoDBClient = Depends(get_mongodb_client)) -> SessionRepository:
    return SessionRepository(mongodb)


def _extract_signature(payload: DoubaoCallbackPayload, request: Request) -> str:
    return (
        request.headers.get("X-Signature")
        or request.headers.get("x-signature")
        or request.headers.get("Signature")
        or request.headers.get("signature")
        or request.headers.get("X-Callback-Signature")
        or payload.signature
        or ""
    )


def _verify_signature(signature: str, raw_body: bytes) -> None:
    secret = os.getenv("VOLCENGINE_CALLBACK_SIGNATURE", "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Callback secret is not configured.",
        )
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing callback signature.",
        )
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid callback signature.",
        )


def _normalize_speaker(raw: str | None) -> Literal["trainee", "ai"]:
    value = (raw or "").strip().lower()
    if value in _AI_SPEAKERS:
        return "ai"
    if value in _TRAINEE_SPEAKERS:
        return "trainee"
    return "trainee"


def _resolve_event_type(payload: DoubaoCallbackPayload) -> str:
    for candidate in (payload.event, payload.event_type, payload.type):
        value = (candidate or "").strip().lower()
        if value in {"transcript_update", "conversation_end", "interrupt"}:
            return value

    if payload.interrupt or (payload.RunStage or "").strip().lower() == "interrupt":
        return "interrupt"
    if payload.subtitleText or payload.transcript or payload.text:
        return "transcript_update"
    if payload.userTranscript or payload.aiTranscript or payload.transcripts:
        return "transcript_update"
    if payload.RunStage == "taskStop":
        return "conversation_end"
    if payload.EventType == 0 and payload.RunStage in {"asrFinish", "answerFinish"}:
        return "transcript_update"
    return "unknown"


async def _resolve_session_id(payload: DoubaoCallbackPayload, repo: SessionRepository) -> str | None:
    direct = (payload.sessionId or payload.session_id or "").strip()
    if direct:
        return direct

    task_id = (payload.taskId or payload.TaskId or "").strip()
    if task_id:
        session = await repo.get_session_by_rtc_task_id(task_id)
        if session:
            return session.id

    room_id = (payload.RoomId or "").strip()
    if room_id:
        session = await repo.get_session_by_rtc_room_id(room_id)
        if session:
            return session.id

    return None


def _candidate_transcripts(payload: DoubaoCallbackPayload) -> list[TranscriptItem]:
    entries = list(payload.transcripts)
    if payload.subtitleText:
        entries.append(
            TranscriptItem(
                speaker=payload.fromUserId,
                transcript=payload.subtitleText,
                sequence=payload.RoundID,
            )
        )
    if payload.transcript or payload.text:
        entries.append(
            TranscriptItem(
                speaker=payload.fromUserId,
                transcript=payload.transcript or payload.text,
                sequence=payload.RoundID,
            )
        )
    if payload.userTranscript:
        entries.append(
            TranscriptItem(
                speaker="trainee",
                transcript=payload.userTranscript,
                sequence=payload.RoundID,
            )
        )
    if payload.aiTranscript:
        base_sequence = payload.RoundID * 2 if payload.RoundID is not None else None
        ai_sequence = (base_sequence + 1) if base_sequence is not None else None
        entries.append(
            TranscriptItem(
                speaker="ai",
                transcript=payload.aiTranscript,
                sequence=ai_sequence,
            )
        )
    return [entry for entry in entries if (entry.transcript or entry.text or "").strip()]


async def _upsert_transcript_turns(
    payload: DoubaoCallbackPayload,
    session_id: str,
    repo: SessionRepository,
) -> dict[str, int]:
    entries = _candidate_transcripts(payload)
    if not entries:
        return {"created": 0, "updated": 0}

    turns = await repo.list_turns(session_id)
    max_sequence = max((turn.sequence for turn in turns), default=-1)
    created = 0
    updated = 0

    for entry in entries:
        transcript = (entry.transcript or entry.text or "").strip()
        if not transcript:
            continue
        speaker = _normalize_speaker(entry.speaker)

        target_turn: TurnRecord | None = None
        if entry.turnId:
            target_turn = next((turn for turn in turns if turn.id == entry.turnId), None)
        if target_turn is None and entry.sequence is not None:
            target_turn = next(
                (
                    turn
                    for turn in turns
                    if turn.sequence == entry.sequence and turn.speaker == speaker
                ),
                None,
            )

        if target_turn:
            result = await repo.update_turn(
                target_turn.id,
                {
                    "transcript": transcript,
                    "asrStatus": "completed" if speaker == "trainee" else target_turn.asr_status,
                    "endedAt": datetime.now(timezone.utc).isoformat(),
                },
            )
            if result:
                updated += 1
                turns = [result if turn.id == result.id else turn for turn in turns]
            continue

        sequence = entry.sequence
        if sequence is None:
            max_sequence += 1
            sequence = max_sequence
        else:
            max_sequence = max(max_sequence, sequence)

        created_turn = await repo.add_turn(
            {
                "sessionId": session_id,
                "sequence": sequence,
                "speaker": speaker,
                "transcript": transcript,
                "audioFileId": "callback",
                "audioUrl": None,
                "asrStatus": "completed" if speaker == "trainee" else None,
                "startedAt": datetime.now(timezone.utc).isoformat(),
                "endedAt": datetime.now(timezone.utc).isoformat(),
                "context": "doubao_callback",
                "latencyMs": None,
            }
        )
        turns.append(created_turn)
        created += 1

    return {"created": created, "updated": updated}


async def _mark_conversation_ended(
    session_id: str,
    repo: SessionRepository,
    payload: DoubaoCallbackPayload,
) -> bool:
    ended_at = datetime.now(timezone.utc).isoformat()
    termination_reason = (
        payload.model_extra.get("reason") if payload.model_extra else None
    ) or "conversation_end"
    updated = await repo.update_session(
        session_id,
        {
            "status": "ended",
            "realtimeState": "ended",
            "endedAt": ended_at,
            "terminationReason": termination_reason,
        },
    )
    return updated is not None


async def _mark_interrupt(
    session_id: str,
    repo: SessionRepository,
    payload: DoubaoCallbackPayload,
) -> bool:
    turns = await repo.list_turns(session_id)
    target = None
    if payload.turnId:
        target = next((turn for turn in turns if turn.id == payload.turnId), None)
    if target is None:
        ai_turns = [turn for turn in turns if turn.speaker == "ai" and not turn.is_interrupted]
        if ai_turns:
            target = max(ai_turns, key=lambda turn: turn.sequence)
    if not target:
        return False

    interrupted_at_ms = payload.EventTime or int(datetime.now(timezone.utc).timestamp() * 1000)
    updated = await repo.update_turn(
        target.id,
        {
            "isInterrupted": True,
            "interruptedAtMs": interrupted_at_ms,
        },
    )
    return updated is not None


@router.post("/callbacks/doubao", status_code=status.HTTP_202_ACCEPTED)
async def receive_doubao_callback(
    request: Request,
    repo: SessionRepository = Depends(_repo),
):
    raw_body = await request.body()
    try:
        raw_payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON payload.",
        ) from exc

    try:
        payload = DoubaoCallbackPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    signature = _extract_signature(payload, request)
    _verify_signature(signature, raw_body)

    event_type = _resolve_event_type(payload)
    session_id = await _resolve_session_id(payload, repo)
    if not session_id and event_type in {"transcript_update", "conversation_end", "interrupt"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing session identity in callback payload.",
        )

    response: dict[str, Any] = {
        "status": "accepted",
        "eventType": event_type,
        "sessionId": session_id,
        "processed": False,
    }

    try:
        if event_type == "transcript_update" and session_id:
            counts = await _upsert_transcript_turns(payload, session_id, repo)
            response.update({"processed": True, "turnsCreated": counts["created"], "turnsUpdated": counts["updated"]})
        elif event_type == "conversation_end" and session_id:
            response["processed"] = await _mark_conversation_ended(session_id, repo, payload)
        elif event_type == "interrupt" and session_id:
            response["processed"] = await _mark_interrupt(session_id, repo, payload)
        else:
            response["ignored"] = True
    except Exception as exc:
        logger.exception("Doubao callback processing failed event=%s session_id=%s", event_type, session_id)
        response["processingError"] = str(exc)

    return response
