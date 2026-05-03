from __future__ import annotations

from typing import Any, cast

import pytest

from app.api.routes.callbacks import DoubaoCallbackPayload, _upsert_transcript_turns
from app.api.routes.e2e_socket import _RealtimeTranscriptState, _persist_upstream_transcript_event
from app.repositories.session_repository import TurnRecord


def _as_string(value: object | None) -> str | None:
    return value if isinstance(value, str) else None


def _as_int(value: object | None) -> int | None:
    return value if isinstance(value, int) else None


def _apply_turn_payload(record: TurnRecord, payload: dict[str, object]) -> TurnRecord:
    data: dict[str, Any] = {
        "id": record.id,
        "session_id": record.session_id,
        "sequence": record.sequence,
        "speaker": record.speaker,
        "transcript": record.transcript,
        "audio_file_id": record.audio_file_id,
        "audio_url": record.audio_url,
        "asr_status": record.asr_status,
        "created_at": record.created_at,
        "started_at": record.started_at,
        "ended_at": record.ended_at,
        "context": record.context,
        "latency_ms": record.latency_ms,
        "is_interrupted": record.is_interrupted,
        "interrupted_at_ms": record.interrupted_at_ms,
    }
    mapping = {
        "sessionId": "session_id",
        "sequence": "sequence",
        "speaker": "speaker",
        "transcript": "transcript",
        "audioFileId": "audio_file_id",
        "audioUrl": "audio_url",
        "asrStatus": "asr_status",
        "createdAt": "created_at",
        "startedAt": "started_at",
        "endedAt": "ended_at",
        "context": "context",
        "latencyMs": "latency_ms",
        "isInterrupted": "is_interrupted",
        "interruptedAtMs": "interrupted_at_ms",
    }
    for key, value in payload.items():
        field = mapping.get(key)
        if field:
            data[field] = value
    return TurnRecord(**data)


class FakeSessionRepo:
    def __init__(self) -> None:
        self.turns: dict[str, TurnRecord] = {}
        self.counter = 0

    async def add_turn(self, payload: dict[str, object]) -> TurnRecord:
        self.counter += 1
        turn_id = f"turn-{self.counter}"
        record = TurnRecord(
            id=turn_id,
            session_id=str(payload.get("sessionId", "")),
            sequence=_as_int(payload.get("sequence")) or 0,
            speaker=str(payload.get("speaker", "")),
            transcript=_as_string(payload.get("transcript")),
            audio_file_id=str(payload.get("audioFileId", "")),
            audio_url=_as_string(payload.get("audioUrl")),
            asr_status=_as_string(payload.get("asrStatus")),
            created_at=_as_string(payload.get("createdAt")),
            started_at=_as_string(payload.get("startedAt")),
            ended_at=_as_string(payload.get("endedAt")),
            context=_as_string(payload.get("context")),
            latency_ms=_as_int(payload.get("latencyMs")),
            is_interrupted=bool(payload.get("isInterrupted", False)),
            interrupted_at_ms=_as_int(payload.get("interruptedAtMs")),
        )
        self.turns[turn_id] = record
        return record

    async def update_turn(self, turn_id: str, payload: dict[str, object]) -> TurnRecord | None:
        record = self.turns.get(turn_id)
        if not record:
            return None
        updated = _apply_turn_payload(record, payload)
        self.turns[turn_id] = updated
        return updated

    async def list_turns(self, session_id: str) -> list[TurnRecord]:
        return [turn for turn in self.turns.values() if turn.session_id == session_id]


@pytest.mark.asyncio
async def test_upstream_transcript_events_persist_user_and_ai_turns() -> None:
    repo = FakeSessionRepo()
    state = _RealtimeTranscriptState()
    session_id = "session-1"

    await _persist_upstream_transcript_event(
        cast(Any, repo),
        session_id,
        state,
        450,
        {"question_id": "question-1"},
    )
    await _persist_upstream_transcript_event(
        cast(Any, repo),
        session_id,
        state,
        451,
        {"question_id": "question-1", "results": [{"text": "Hello there", "is_interim": True}]},
    )
    await _persist_upstream_transcript_event(
        cast(Any, repo),
        session_id,
        state,
        451,
        {"question_id": "question-1", "results": [{"text": "Hello there", "is_interim": False}]},
    )
    await _persist_upstream_transcript_event(
        cast(Any, repo),
        session_id,
        state,
        459,
        {"question_id": "question-1"},
    )
    await _persist_upstream_transcript_event(
        cast(Any, repo),
        session_id,
        state,
        550,
        {"question_id": "question-1", "reply_id": "reply-1", "content": "Thanks for raising that."},
    )
    await _persist_upstream_transcript_event(
        cast(Any, repo),
        session_id,
        state,
        559,
        {"question_id": "question-1", "reply_id": "reply-1"},
    )

    turns = sorted(await repo.list_turns(session_id), key=lambda turn: turn.sequence)
    assert len(turns) == 2

    trainee_turn, ai_turn = turns
    assert trainee_turn.speaker == "trainee"
    assert trainee_turn.sequence == 0
    assert trainee_turn.transcript == "Hello there"
    assert trainee_turn.asr_status == "completed"
    assert trainee_turn.context == "volcengine_e2e:user:question-1"
    assert trainee_turn.ended_at is not None

    assert ai_turn.speaker == "ai"
    assert ai_turn.sequence == 1
    assert ai_turn.transcript == "Thanks for raising that."
    assert ai_turn.context == "volcengine_e2e:ai|reply:reply-1|question:question-1"
    assert ai_turn.ended_at is not None


@pytest.mark.asyncio
async def test_streaming_llm_text_accumulates_across_tokens() -> None:
    repo = FakeSessionRepo()
    state = _RealtimeTranscriptState()
    session_id = "session-1"

    # User speaks
    await _persist_upstream_transcript_event(
        cast(Any, repo), session_id, state,
        450, {"question_id": "question-1"},
    )
    await _persist_upstream_transcript_event(
        cast(Any, repo), session_id, state,
        451, {"question_id": "question-1", "results": [{"text": "Hello", "is_interim": False}]},
    )
    await _persist_upstream_transcript_event(
        cast(Any, repo), session_id, state,
        459, {"question_id": "question-1"},
    )

    # AI streams token-by-token via event 550
    for token in ["I ", "understand ", "your ", "concern", "."]:
        await _persist_upstream_transcript_event(
            cast(Any, repo), session_id, state,
            550, {"question_id": "question-1", "reply_id": "reply-1", "content": token},
        )

    # Before LLM_TEXT_END, DB should NOT have the AI turn yet
    turns_before = await repo.list_turns(session_id)
    assert all(t.speaker != "ai" for t in turns_before)

    # Final event triggers persistence of accumulated text
    await _persist_upstream_transcript_event(
        cast(Any, repo), session_id, state,
        559, {"question_id": "question-1", "reply_id": "reply-1"},
    )

    turns = sorted(await repo.list_turns(session_id), key=lambda t: t.sequence)
    assert len(turns) == 2

    ai_turn = turns[1]
    assert ai_turn.speaker == "ai"
    assert ai_turn.transcript == "I understand your concern."
    assert ai_turn.ended_at is not None


@pytest.mark.asyncio
async def test_callback_transcript_update_reuses_socket_persisted_turn_by_context_identifier() -> None:
    repo = FakeSessionRepo()
    existing = await repo.add_turn(
        {
            "sessionId": "session-1",
            "sequence": 0,
            "speaker": "trainee",
            "transcript": "Initial interim text",
            "audioFileId": "",
            "audioUrl": None,
            "asrStatus": "in_progress",
            "startedAt": "2026-01-01T00:00:00+00:00",
            "endedAt": None,
            "context": "volcengine_e2e:user:question-1",
            "latencyMs": None,
        }
    )

    counts = await _upsert_transcript_turns(
        DoubaoCallbackPayload.model_validate(
            {
                "event": "transcript_update",
                "sessionId": "session-1",
                "question_id": "question-1",
                "userTranscript": "Final user transcript",
            }
        ),
        "session-1",
        cast(Any, repo),
    )

    turns = await repo.list_turns("session-1")
    assert counts == {"created": 0, "updated": 1}
    assert len(turns) == 1
    assert turns[0].id == existing.id
    assert turns[0].transcript == "Final user transcript"
    assert turns[0].asr_status == "completed"
