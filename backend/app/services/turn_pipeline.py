from __future__ import annotations

import base64
import asyncio
from datetime import datetime, timezone
from typing import Any

from app.api.routes.session_socket import hub
from app.clients.leancloud import LeanCloudClient
from app.clients.llm import QwenClient
from app.config import load_settings
from app.repositories.session_repository import SessionRepository

QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen3-omni-flash"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_qwen_text(response: dict[str, Any]) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "")


async def enqueue_turn_pipeline(*, session_id: str, turn_id: str, audio_base64: str) -> None:
    await _process_turn(session_id=session_id, turn_id=turn_id, audio_base64=audio_base64)


async def _process_turn(*, session_id: str, turn_id: str, audio_base64: str) -> None:
    settings = load_settings()
    lc_client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    qwen_client = QwenClient(
        base_url=QWEN_BASE_URL,
        api_key=settings.dashscope_api_key,
    )
    repo = SessionRepository(lc_client)

    try:
        audio_bytes = base64.b64decode(audio_base64)
        upload = await lc_client.upload_file(
            f"turn-{turn_id}.mp3", audio_bytes, "audio/mpeg"
        )
        file_id = upload.get("objectId") or upload.get("name")
        await repo.update_turn(
            turn_id,
            {
                "audioFileId": file_id,
                "audioUrl": upload.get("url"),
                "asrStatus": "pending",
                "updatedAt": _utc_now(),
            },
        )

        turns = await repo.list_turns(session_id)
        max_sequence = max((turn.sequence for turn in turns), default=-1)

        generation_task = qwen_client.generate(
            {
                "model": QWEN_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an AI coach."},
                    {"role": "user", "content": "Respond to the trainee."},
                ],
            }
        )
        asr_task = qwen_client.asr({"model": QWEN_MODEL, "input": audio_base64})

        generation_response, asr_response = await asyncio.gather(
            generation_task, asr_task, return_exceptions=True
        )

        transcript = ""
        if not isinstance(generation_response, Exception):
            transcript = _parse_qwen_text(generation_response)

        ai_turn = await repo.add_turn(
            {
                "sessionId": session_id,
                "sequence": max_sequence + 1,
                "speaker": "ai",
                "transcript": transcript or None,
                "audioFileId": file_id or "pending",
                "audioUrl": upload.get("url"),
                "asrStatus": None,
                "createdAt": _utc_now(),
                "startedAt": _utc_now(),
                "endedAt": _utc_now(),
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

        if isinstance(asr_response, Exception):
            await repo.update_turn(turn_id, {"asrStatus": "failed"})
        else:
            await repo.update_turn(
                turn_id,
                {"asrStatus": "completed", "transcript": asr_response.get("text")},
            )
    finally:
        await qwen_client.close()
        await lc_client.close()
