from __future__ import annotations

import asyncio
import base64
import gzip
import json
import logging
import uuid
from array import array
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import WebSocketException

from app.config import SettingsError, load_settings
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.session_repository import SessionRepository
from app.services import opening_prompt_service
from app.services.session_service import finalize_session
from app.services.e2e_prompt_builder import (
    build_e2e_system_prompt,
    resolve_bot_name,
    resolve_opening_content,
)

router = APIRouter()
logger = logging.getLogger(__name__)

PROTOCOL_VERSION = 0b0001
CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111
MSG_WITH_EVENT = 0b0100
NO_SERIALIZATION = 0b0000
JSON_SERIALIZATION = 0b0001
GZIP_COMPRESSION = 0b0001

EVENT_START_CONNECTION = 1
EVENT_FINISH_CONNECTION = 2
EVENT_START_SESSION = 100
EVENT_FINISH_SESSION = 102
EVENT_TASK_REQUEST = 200
EVENT_TASK_COMMIT = 201
EVENT_OPENING_REQUEST = 300

EVENT_TTS_RESPONSE = 352
EVENT_TTS_ENDED = 359
EVENT_LLM_TEXT = 550
EVENT_LLM_TEXT_END = 559

E2E_RESOURCE_ID = "volc.speech.dialog"
E2E_FIXED_APP_KEY = "PlgvMymc7f3tQnJ6"


@dataclass(frozen=True)
class E2EConfig:
    ws_url: str
    app_id: str
    access_key: str
    model: str | None
    resource_id: str
    app_key: str
    speaker: str | None


@dataclass
class _RealtimeTranscriptState:
    next_user_sequence: int = 0
    active_question_id: str | None = None
    active_reply_id: str | None = None
    user_turn_ids_by_question: dict[str, str] = field(default_factory=dict)
    user_sequences_by_question: dict[str, int] = field(default_factory=dict)
    ai_turn_ids_by_reply: dict[str, str] = field(default_factory=dict)
    ai_sequences_by_reply: dict[str, int] = field(default_factory=dict)
    ai_accumulated_text_by_reply: dict[str, str] = field(default_factory=dict)


def _load_e2e_config() -> E2EConfig:
    settings = load_settings()
    ws_url = (settings.volcengine_e2e_ws_url or "wss://openspeech.bytedance.com/api/v3/realtime/dialogue").strip()
    app_id = (settings.realtime_voice_model_app_id or settings.volcengine_e2e_app_id or "").strip()
    access_key = (settings.realtime_voice_model_access_token or settings.volcengine_e2e_api_key or "").strip()
    model = (settings.volcengine_e2e_model or "").strip() or None
    resource_id = (settings.volcengine_e2e_resource_id or E2E_RESOURCE_ID).strip()
    app_key = (settings.volcengine_e2e_app_key or E2E_FIXED_APP_KEY).strip()
    speaker = (settings.volcengine_e2e_speaker or "").strip() or None

    if not app_id:
        raise SettingsError("Missing required environment variable: REALTIME_VOICE_MODEL_APP_ID")
    if not access_key:
        raise SettingsError("Missing required environment variable: REALTIME_VOICE_MODEL_ACCESS_TOKEN")
    return E2EConfig(
        ws_url=ws_url,
        app_id=app_id,
        access_key=access_key,
        model=model,
        resource_id=resource_id,
        app_key=app_key,
        speaker=speaker,
    )


def _generate_header(
    *,
    message_type: int,
    message_type_specific_flags: int = MSG_WITH_EVENT,
    serialization: int = JSON_SERIALIZATION,
    compression: int = GZIP_COMPRESSION,
) -> bytearray:
    header = bytearray()
    header_size = 1
    header.append((PROTOCOL_VERSION << 4) | header_size)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serialization << 4) | compression)
    header.append(0x00)
    return header


def _build_full_request(event: int, payload_obj: dict[str, Any], *, session_id: str | None = None) -> bytes:
    payload_bytes = gzip.compress(json.dumps(payload_obj).encode("utf-8"))
    request = _generate_header(message_type=CLIENT_FULL_REQUEST)
    request.extend(int(event).to_bytes(4, "big"))
    if session_id is not None:
        sid = session_id.encode("utf-8")
        request.extend(len(sid).to_bytes(4, "big"))
        request.extend(sid)
    request.extend(len(payload_bytes).to_bytes(4, "big"))
    request.extend(payload_bytes)
    return bytes(request)


def _build_audio_request(event: int, session_id: str, pcm_bytes: bytes) -> bytes:
    payload_bytes = gzip.compress(pcm_bytes)
    request = _generate_header(
        message_type=CLIENT_AUDIO_ONLY_REQUEST,
        serialization=NO_SERIALIZATION,
    )
    request.extend(int(event).to_bytes(4, "big"))
    sid = session_id.encode("utf-8")
    request.extend(len(sid).to_bytes(4, "big"))
    request.extend(sid)
    request.extend(len(payload_bytes).to_bytes(4, "big"))
    request.extend(payload_bytes)
    return bytes(request)


def _parse_upstream_packet(packet: bytes) -> dict[str, Any]:
    if not packet:
        return {}

    header_size = packet[0] & 0x0F
    message_type = packet[1] >> 4
    flags = packet[1] & 0x0F
    serialization = packet[2] >> 4
    compression = packet[2] & 0x0F
    payload = packet[header_size * 4 :]

    result: dict[str, Any] = {
        "message_type": message_type,
        "event": None,
        "payload": None,
        "error_code": None,
    }

    if message_type in {SERVER_FULL_RESPONSE, SERVER_ACK}:
        idx = 0
        if flags & 0b0010:
            idx += 4
        event = None
        if flags & MSG_WITH_EVENT:
            if len(payload) < idx + 4:
                return result
            event = int.from_bytes(payload[idx : idx + 4], "big", signed=False)
            idx += 4
        result["event"] = event

        if len(payload) < idx + 4:
            return result
        sid_size = int.from_bytes(payload[idx : idx + 4], "big", signed=True)
        idx += 4 + max(0, sid_size)

        if len(payload) < idx + 4:
            return result
        payload_size = int.from_bytes(payload[idx : idx + 4], "big", signed=False)
        idx += 4
        raw_payload = payload[idx : idx + payload_size]

        if compression == GZIP_COMPRESSION:
            raw_payload = gzip.decompress(raw_payload)

        if serialization == JSON_SERIALIZATION:
            result["payload"] = json.loads(raw_payload.decode("utf-8"))
        else:
            result["payload"] = raw_payload
        return result

    if message_type == SERVER_ERROR_RESPONSE:
        if len(payload) >= 8:
            result["error_code"] = int.from_bytes(payload[:4], "big", signed=False)
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            raw_payload = payload[8 : 8 + payload_size]
            if compression == GZIP_COMPRESSION:
                raw_payload = gzip.decompress(raw_payload)
            if serialization == JSON_SERIALIZATION:
                result["payload"] = json.loads(raw_payload.decode("utf-8"))
            else:
                result["payload"] = raw_payload
        return result

    return result


def _float32le_to_int16le(raw_audio: bytes) -> bytes:
    if not raw_audio:
        return b""
    floats = array("f")
    floats.frombytes(raw_audio)
    if floats.itemsize != 4:
        return b""
    if array("I", [1]).tobytes()[0] != 1:
        floats.byteswap()
    ints = array("h")
    for value in floats:
        if value > 1.0:
            value = 1.0
        elif value < -1.0:
            value = -1.0
        ints.append(int(value * 32767))
    return ints.tobytes()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_identifier(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _user_turn_context(question_id: str | None) -> str:
    if question_id:
        return f"volcengine_e2e:user:{question_id}"
    return "volcengine_e2e:user"


def _ai_turn_context(question_id: str | None, reply_id: str | None) -> str:
    parts = ["volcengine_e2e:ai"]
    if reply_id:
        parts.append(f"reply:{reply_id}")
    if question_id:
        parts.append(f"question:{question_id}")
    return "|".join(parts)


async def _build_transcript_state(
    repo: SessionRepository | None,
    session_id: str,
) -> _RealtimeTranscriptState:
    if repo is None or not session_id:
        return _RealtimeTranscriptState()

    turns = await repo.list_turns(session_id)
    max_even_sequence = max(
        (turn.sequence for turn in turns if turn.speaker == "trainee"),
        default=-2,
    )
    return _RealtimeTranscriptState(next_user_sequence=max_even_sequence + 2)


def _resolve_question_id_from_payload(
    payload: dict[str, Any] | None,
    state: _RealtimeTranscriptState,
) -> str | None:
    if not isinstance(payload, dict):
        return state.active_question_id
    return (
        _normalize_identifier(payload.get("question_id"))
        or _normalize_identifier(payload.get("questionId"))
        or state.active_question_id
    )


def _resolve_reply_id_from_payload(
    payload: dict[str, Any] | None,
    state: _RealtimeTranscriptState,
) -> str | None:
    if not isinstance(payload, dict):
        return state.active_reply_id
    return (
        _normalize_identifier(payload.get("reply_id"))
        or _normalize_identifier(payload.get("replyId"))
        or state.active_reply_id
    )


async def _ensure_user_turn(
    repo: SessionRepository,
    session_id: str,
    state: _RealtimeTranscriptState,
    *,
    question_id: str | None,
) -> tuple[str, int]:
    if question_id and question_id in state.user_turn_ids_by_question:
        return (
            state.user_turn_ids_by_question[question_id],
            state.user_sequences_by_question[question_id],
        )

    sequence = state.next_user_sequence
    state.next_user_sequence += 2
    created_turn = await repo.add_turn(
        {
            "sessionId": session_id,
            "sequence": sequence,
            "speaker": "trainee",
            "transcript": None,
            "audioFileId": "",
            "audioUrl": None,
            "asrStatus": "in_progress",
            "startedAt": _utc_now_iso(),
            "endedAt": None,
            "context": _user_turn_context(question_id),
            "latencyMs": None,
        }
    )
    if question_id:
        state.user_turn_ids_by_question[question_id] = created_turn.id
        state.user_sequences_by_question[question_id] = sequence
    state.active_question_id = question_id
    return created_turn.id, sequence


async def _ensure_ai_turn(
    repo: SessionRepository,
    session_id: str,
    state: _RealtimeTranscriptState,
    *,
    question_id: str | None,
    reply_id: str | None,
) -> tuple[str, int]:
    if reply_id and reply_id in state.ai_turn_ids_by_reply:
        turn_id = state.ai_turn_ids_by_reply[reply_id]
        sequence = state.ai_sequences_by_reply.get(reply_id)
        if sequence is not None:
            return turn_id, sequence

    if question_id and question_id in state.user_sequences_by_question:
        sequence = state.user_sequences_by_question[question_id] + 1
    else:
        sequence = state.next_user_sequence + 1

    created_turn = await repo.add_turn(
        {
            "sessionId": session_id,
            "sequence": sequence,
            "speaker": "ai",
            "transcript": None,
            "audioFileId": "",
            "audioUrl": None,
            "asrStatus": None,
            "startedAt": _utc_now_iso(),
            "endedAt": None,
            "context": _ai_turn_context(question_id, reply_id),
            "latencyMs": None,
        }
    )
    if reply_id:
        state.ai_turn_ids_by_reply[reply_id] = created_turn.id
        state.ai_sequences_by_reply[reply_id] = sequence
    state.active_question_id = question_id or state.active_question_id
    state.active_reply_id = reply_id
    return created_turn.id, sequence


async def _persist_user_transcript(
    repo: SessionRepository | None,
    session_id: str,
    state: _RealtimeTranscriptState,
    *,
    question_id: str | None,
    transcript: str,
    is_final: bool,
) -> None:
    if repo is None or not session_id:
        return

    normalized = transcript.strip()
    if not normalized:
        return

    turn_id, _ = await _ensure_user_turn(repo, session_id, state, question_id=question_id)
    payload: dict[str, Any] = {
        "transcript": normalized,
        "asrStatus": "completed" if is_final else "in_progress",
    }
    if is_final:
        payload["endedAt"] = _utc_now_iso()
    await repo.update_turn(turn_id, payload)
    state.active_question_id = question_id or state.active_question_id


async def _finalize_user_transcript(
    repo: SessionRepository | None,
    state: _RealtimeTranscriptState,
    *,
    question_id: str | None,
) -> None:
    if repo is None:
        return

    target_question_id = question_id or state.active_question_id
    if not target_question_id:
        return
    turn_id = state.user_turn_ids_by_question.get(target_question_id)
    if not turn_id:
        return
    await repo.update_turn(
        turn_id,
        {
            "asrStatus": "completed",
            "endedAt": _utc_now_iso(),
        },
    )
    state.active_question_id = target_question_id


async def _persist_ai_transcript(
    repo: SessionRepository | None,
    session_id: str,
    state: _RealtimeTranscriptState,
    *,
    question_id: str | None,
    reply_id: str | None,
    transcript: str,
    is_final: bool,
) -> None:
    if repo is None or not session_id:
        return

    normalized = transcript.strip()
    if not normalized:
        return

    turn_id, _ = await _ensure_ai_turn(
        repo,
        session_id,
        state,
        question_id=question_id,
        reply_id=reply_id,
    )
    payload: dict[str, Any] = {"transcript": normalized}
    if is_final:
        payload["endedAt"] = _utc_now_iso()
    await repo.update_turn(turn_id, payload)
    state.active_question_id = question_id or state.active_question_id
    state.active_reply_id = reply_id or state.active_reply_id


async def _finalize_ai_transcript(
    repo: SessionRepository | None,
    state: _RealtimeTranscriptState,
    *,
    reply_id: str | None,
) -> None:
    if repo is None:
        return
    target_reply_id = reply_id or state.active_reply_id
    if not target_reply_id:
        return
    turn_id = state.ai_turn_ids_by_reply.get(target_reply_id)
    if not turn_id:
        return
    await repo.update_turn(turn_id, {"endedAt": _utc_now_iso()})
    state.active_reply_id = target_reply_id


async def _persist_upstream_transcript_event(
    repo: SessionRepository | None,
    session_id: str,
    state: _RealtimeTranscriptState,
    event: int | None,
    payload: Any,
) -> None:
    if repo is None or not session_id or not isinstance(payload, dict):
        return

    if event == 450:
        state.active_question_id = _resolve_question_id_from_payload(payload, state)
        return

    if event == 451:
        question_id = _resolve_question_id_from_payload(payload, state)
        results = payload.get("results")
        if not isinstance(results, list):
            return
        latest_text = ""
        latest_final = False
        for result in results:
            if not isinstance(result, dict):
                continue
            text = result.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            latest_text = text.strip()
            latest_final = _coerce_bool(result.get("is_interim")) is False
        if latest_text:
            await _persist_user_transcript(
                repo,
                session_id,
                state,
                question_id=question_id,
                transcript=latest_text,
                is_final=latest_final,
            )
        return

    if event == 459:
        await _finalize_user_transcript(
            repo,
            state,
            question_id=_resolve_question_id_from_payload(payload, state),
        )
        return

    if event == EVENT_LLM_TEXT:
        content = payload.get("content")
        if not isinstance(content, str):
            return
        reply_id = _resolve_reply_id_from_payload(payload, state)
        target = reply_id or state.active_reply_id
        if target:
            state.ai_accumulated_text_by_reply[target] = (
                state.ai_accumulated_text_by_reply.get(target, "") + content
            )
        return

    if event == EVENT_LLM_TEXT_END:
        reply_id = _resolve_reply_id_from_payload(payload, state)
        target = reply_id or state.active_reply_id
        accumulated = state.ai_accumulated_text_by_reply.pop(target, "") if target else ""
        if accumulated.strip():
            await _persist_ai_transcript(
                repo,
                session_id,
                state,
                question_id=_resolve_question_id_from_payload(payload, state),
                reply_id=reply_id,
                transcript=accumulated,
                is_final=True,
            )
        await _finalize_ai_transcript(
            repo,
            state,
            reply_id=reply_id,
        )


async def _recv_client_config(client_ws: WebSocket) -> dict[str, Any]:
    while True:
        message = await client_ws.receive()
        if message.get("type") == "websocket.disconnect":
            raise WebSocketDisconnect()
        text = message.get("text")
        if text is None:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "session.update":
            session = payload.get("session")
            if isinstance(session, dict):
                return session


def _build_start_session_payload(
    config: E2EConfig,
    session_id: str,
    client_session: dict[str, Any],
    scenario: Any | None = None,
    language: str = "en",
) -> dict[str, Any]:
    model = config.model
    maybe_model = client_session.get("model")
    if isinstance(maybe_model, str) and maybe_model.strip():
        model = maybe_model.strip()

    speaker = config.speaker
    maybe_speaker = client_session.get("speaker")
    if isinstance(maybe_speaker, str) and maybe_speaker.strip():
        speaker = maybe_speaker.strip()

    payload: dict[str, Any] = {
        "asr": {"extra": {"enable_custom_vad": True, "end_smooth_window_ms": 2000}},
        "tts": {
            "audio_config": {
                "channel": 1,
                "format": "pcm",
                "sample_rate": 24000,
            },
        },
        "dialog": {
            "bot_name": resolve_bot_name(scenario),
            "system_role": build_e2e_system_prompt(scenario, language),
            "dialog_id": session_id,
            "extra": {
                "input_mod": "keep_alive",
                "strict_audit": False,
            },
        },
    }
    if model:
        payload["dialog"]["extra"]["model"] = model
    if speaker:
        payload["tts"]["speaker"] = speaker
    return payload


def _build_session_ready_payload(
    start_payload: dict[str, Any],
    opening_content: str,
    *,
    send_debug_prompts: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "session.ready"}
    if send_debug_prompts:
        payload["debug"] = {
            "systemPrompt": start_payload["dialog"]["system_role"],
            "openingText": opening_content.strip(),
        }
    return payload


async def _pipe_client_audio(client_ws: WebSocket, upstream_ws, session_id: str) -> str | None:
    while True:
        message = await client_ws.receive()
        if message.get("type") == "websocket.disconnect":
            return None
        text = message.get("text")
        if text is None:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        event_type = payload.get("type")
        if event_type == "input_audio_buffer.append":
            audio_b64 = payload.get("audio")
            if isinstance(audio_b64, str) and audio_b64:
                pcm_bytes = base64.b64decode(audio_b64)
                await upstream_ws.send(_build_audio_request(EVENT_TASK_REQUEST, session_id, pcm_bytes))
        elif event_type == "input_audio_buffer.commit":
            await upstream_ws.send(_build_full_request(EVENT_TASK_COMMIT, {}, session_id=session_id))
        elif event_type == "finish_session":
            await upstream_ws.send(_build_full_request(EVENT_FINISH_SESSION, {}, session_id=session_id))
            return "manual"


async def _safe_send_json(websocket: WebSocket, payload: dict[str, Any]) -> None:
    try:
        await websocket.send_json(payload)
    except RuntimeError:
        return


async def _persist_callback_session_correlation(
    repo: SessionRepository,
    session_id: str,
    runtime_session_id: str,
) -> None:
    if not session_id or not runtime_session_id:
        return

    await repo.update_session(
        session_id,
        {
            "mode": "realtime",
            "rtcRoomId": runtime_session_id,
            "realtimeState": "connecting",
        },
    )


async def _persist_opening_prompt(
    repo: SessionRepository,
    session_id: str,
    opening_content: str,
) -> None:
    persisted_opening = opening_content.strip()
    if not session_id or not persisted_opening:
        return

    await repo.update_session(
        session_id,
        {
            "openingPrompt": persisted_opening,
        },
    )


async def _finalize_realtime_session(
    repo: SessionRepository | None,
    session_id: str,
    *,
    termination_reason: str | None,
) -> None:
    if repo is None or not session_id:
        return

    payload: dict[str, Any] = {
        "status": "ended",
        "realtimeState": "ended",
        "endedAt": datetime.now(timezone.utc).isoformat(),
    }
    if termination_reason:
        payload["terminationReason"] = termination_reason
    await finalize_session(repo, session_id, payload)


async def _pipe_upstream_events(
    client_ws: WebSocket,
    upstream_ws,
    repo: SessionRepository | None,
    session_id: str,
) -> None:
    transcript_state = await _build_transcript_state(repo, session_id)
    async for packet in upstream_ws:
        if isinstance(packet, str):
            continue
        parsed = _parse_upstream_packet(packet)
        event = parsed.get("event")
        payload = parsed.get("payload")

        await _persist_upstream_transcript_event(
            repo,
            session_id,
            transcript_state,
            event,
            payload,
        )

        if parsed.get("message_type") == SERVER_ERROR_RESPONSE:
            await client_ws.send_json(
                {
                    "type": "error",
                    "message": f"Upstream error code={parsed.get('error_code')} payload={payload}",
                }
            )
            continue

        if event == EVENT_TTS_RESPONSE and isinstance(payload, (bytes, bytearray)):
            pcm_int16 = _float32le_to_int16le(bytes(payload))
            if pcm_int16:
                await client_ws.send_json(
                    {
                        "type": "response.audio.delta",
                        "delta": base64.b64encode(pcm_int16).decode("utf-8"),
                    }
                )
        elif event == EVENT_TTS_ENDED:
            await client_ws.send_json({"type": "response.audio.done"})
        elif event == EVENT_LLM_TEXT and isinstance(payload, dict):
            content = payload.get("content")
            if isinstance(content, str) and content:
                await client_ws.send_json({"type": "response.text.delta", "delta": content})
        elif event == EVENT_LLM_TEXT_END:
            await client_ws.send_json({"type": "response.text.done"})


def _extract_upstream_error(parsed: dict[str, Any]) -> str | None:
    payload = parsed.get("payload")
    if parsed.get("message_type") == SERVER_ERROR_RESPONSE:
        return f"code={parsed.get('error_code')} payload={payload}"
    if isinstance(payload, dict):
        code = payload.get("code")
        message = payload.get("message") or payload.get("msg")
        if code not in (None, 0):
            return f"code={code} message={message}"
    return None


@router.websocket("/ws/e2e/sessions/{session_id}")
async def e2e_voice_socket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        config = _load_e2e_config()
    except SettingsError as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close(code=1011)
        return

    runtime_session_id = session_id or str(uuid.uuid4())
    try:
        client_session_cfg = await asyncio.wait_for(_recv_client_config(websocket), timeout=10)
    except asyncio.TimeoutError:
        await websocket.send_json({"type": "error", "message": "Missing initial session.update from client"})
        await websocket.close(code=1002)
        return
    except WebSocketDisconnect:
        return

    send_debug_prompts = bool(client_session_cfg.get("debug_prompts"))

    scenario = None
    session_repository: SessionRepository | None = None
    session_record = None
    language = "en"
    try:
        mongodb = websocket.app.state.mongodb
        session_repository = SessionRepository(mongodb)
        scenario_repository = ScenarioRepository(mongodb)
        session_record = await asyncio.wait_for(
            session_repository.get_session(session_id),
            timeout=5,
        )
        if session_record is None:
            raise LookupError(f"Session not found: {session_id}")
        if session_record.language in {"en", "zh"}:
            language = session_record.language
        if not session_record.scenario_id:
            raise LookupError(f"Session missing scenario_id: {session_id}")
        scenario = await asyncio.wait_for(
            scenario_repository.get(session_record.scenario_id),
            timeout=5,
        )
        if scenario is None:
            raise LookupError(f"Scenario not found: {session_record.scenario_id}")
    except Exception as exc:
        logger.warning(
            "Falling back to default realtime prompt for session %s: %s",
            session_id,
            exc,
        )
        scenario = None
        language = "en"

    if session_repository is not None and session_record is not None:
        await _persist_callback_session_correlation(
            session_repository,
            session_id,
            runtime_session_id,
        )

    headers = {
        "X-Api-App-ID": config.app_id,
        "X-Api-Access-Key": config.access_key,
        "X-Api-Resource-Id": config.resource_id,
        "X-Api-App-Key": config.app_key,
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }

    try:
        async with ws_connect(
            config.ws_url,
            additional_headers=headers,
            proxy=None,
            max_size=None,
        ) as upstream_ws:
            await upstream_ws.send(_build_full_request(EVENT_START_CONNECTION, {}))
            start_conn_ack = await upstream_ws.recv()
            if not isinstance(start_conn_ack, (bytes, bytearray)):
                await websocket.send_json({"type": "error", "message": "Invalid StartConnection response from upstream"})
                await websocket.close(code=1011)
                return
            start_conn_parsed = _parse_upstream_packet(bytes(start_conn_ack))
            start_conn_error = _extract_upstream_error(start_conn_parsed)
            if start_conn_error:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"StartConnection failed: {start_conn_error}",
                    }
                )
                await websocket.close(code=1011)
                return

            start_payload = _build_start_session_payload(
                config,
                runtime_session_id,
                client_session_cfg,
                scenario=scenario,
                language=language,
            )
            await upstream_ws.send(_build_full_request(EVENT_START_SESSION, start_payload, session_id=runtime_session_id))
            start_session_ack = await upstream_ws.recv()
            if not isinstance(start_session_ack, (bytes, bytearray)):
                await websocket.send_json({"type": "error", "message": "Invalid StartSession response from upstream"})
                await websocket.close(code=1011)
                return
            start_session_parsed = _parse_upstream_packet(bytes(start_session_ack))
            start_session_error = _extract_upstream_error(start_session_parsed)
            if start_session_error:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"StartSession failed: {start_session_error}",
                    }
                )
                await websocket.close(code=1011)
                return

            if session_repository is not None and session_record is not None:
                await session_repository.update_session(
                    session_id,
                    {
                        "mode": "realtime",
                        "realtimeState": "active",
                    },
                )

            send_opening_flag = client_session_cfg.get("send_opening")
            should_send_opening = True if send_opening_flag is None else bool(send_opening_flag)
            opening_content = ""
            if should_send_opening:
                opening_content, needs_llm_generation = resolve_opening_content(
                    scenario,
                    language,
                    None,
                )
                if needs_llm_generation and scenario is not None:
                    try:
                        opening_content, _, _, _ = await opening_prompt_service.generate_opening_prompt(
                            scenario=scenario,
                            language=language,
                        )
                    except Exception as exc:
                        logger.warning(
                            "Falling back to casual opening for session %s: %s",
                            session_id,
                            exc,
                        )
                        opening_content, _ = resolve_opening_content(None, language, None)
                await upstream_ws.send(
                    _build_full_request(
                        EVENT_OPENING_REQUEST,
                        {"content": opening_content.strip()},
                        session_id=runtime_session_id,
                    )
                )
                if session_repository is not None and session_record is not None:
                    await _persist_opening_prompt(
                        session_repository,
                        session_id,
                        opening_content,
                    )

            await _safe_send_json(
                websocket,
                _build_session_ready_payload(
                    start_payload,
                    opening_content,
                    send_debug_prompts=send_debug_prompts,
                ),
            )

            to_upstream = asyncio.create_task(_pipe_client_audio(websocket, upstream_ws, runtime_session_id))
            to_client = asyncio.create_task(
                _pipe_upstream_events(
                    websocket,
                    upstream_ws,
                    session_repository,
                    session_id,
                )
            )

            termination_reason: str | None = None
            done, pending = await asyncio.wait(
                {to_upstream, to_client},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                if task.cancelled():
                    continue
                exc = task.exception()
                if exc is not None:
                    raise exc

            if to_upstream in done:
                termination_reason = to_upstream.result()
            elif to_client in done:
                termination_reason = "upstream_finish"

            try:
                await upstream_ws.send(_build_full_request(EVENT_FINISH_SESSION, {}, session_id=runtime_session_id))
                await upstream_ws.send(_build_full_request(EVENT_FINISH_CONNECTION, {}))
            except WebSocketException:
                pass
            await _finalize_realtime_session(
                session_repository,
                session_id,
                termination_reason=termination_reason,
            )
    except WebSocketException as exc:
        await _safe_send_json(websocket, {"type": "error", "message": f"Upstream websocket error: {exc}"})
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            return
        await _finalize_realtime_session(
            session_repository,
            session_id,
            termination_reason=None,
        )
    except Exception as exc:
        await _safe_send_json(websocket, {"type": "error", "message": f"Voice gateway error: {exc}"})
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            return
        await _finalize_realtime_session(
            session_repository,
            session_id,
            termination_reason=None,
        )
