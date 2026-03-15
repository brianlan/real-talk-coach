from __future__ import annotations

import asyncio
import base64
import gzip
import json
import random
import uuid
from array import array
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import WebSocketException

from app.config import SettingsError, load_settings

router = APIRouter()

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


def _build_start_session_payload(config: E2EConfig, session_id: str, client_session: dict[str, Any]) -> dict[str, Any]:
    model = config.model
    maybe_model = client_session.get("model")
    if isinstance(maybe_model, str) and maybe_model.strip():
        model = maybe_model.strip()

    speaker = config.speaker
    maybe_speaker = client_session.get("speaker")
    if isinstance(maybe_speaker, str) and maybe_speaker.strip():
        speaker = maybe_speaker.strip()

    payload: dict[str, Any] = {
        "asr": {"extra": {"end_smooth_window_ms": 500}},
        "tts": {
            "audio_config": {
                "channel": 1,
                "format": "pcm",
                "sample_rate": 24000,
            },
        },
        "dialog": {
            "bot_name": "Real Talk Coach",
            "system_role": "You are an AI communication coach helping the user practice difficult conversations.",
            "dialog_id": session_id,
            "extra": {
                "strict_audit": False,
            },
        },
    }
    if model:
        payload["dialog"]["extra"]["model"] = model
    if speaker:
        payload["tts"]["speaker"] = speaker
    return payload


async def _pipe_client_audio(client_ws: WebSocket, upstream_ws, session_id: str) -> None:
    while True:
        message = await client_ws.receive()
        if message.get("type") == "websocket.disconnect":
            return
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


async def _safe_send_json(websocket: WebSocket, payload: dict[str, Any]) -> None:
    try:
        await websocket.send_json(payload)
    except RuntimeError:
        return


async def _pipe_upstream_events(client_ws: WebSocket, upstream_ws) -> None:
    async for packet in upstream_ws:
        if isinstance(packet, str):
            continue
        parsed = _parse_upstream_packet(packet)
        event = parsed.get("event")
        payload = parsed.get("payload")

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

            start_payload = _build_start_session_payload(config, runtime_session_id, client_session_cfg)
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

            opening_content = client_session_cfg.get("opening")
            if not isinstance(opening_content, str) or not opening_content.strip():
                opening_content = "Hi, I am your AI coach. Tell me what you want to practice and we can begin now."
            await upstream_ws.send(
                _build_full_request(
                    EVENT_OPENING_REQUEST,
                    {"content": opening_content.strip()},
                    session_id=runtime_session_id,
                )
            )

            await _safe_send_json(websocket, {"type": "session.ready"})

            to_upstream = asyncio.create_task(_pipe_client_audio(websocket, upstream_ws, runtime_session_id))
            to_client = asyncio.create_task(_pipe_upstream_events(websocket, upstream_ws))

            done, pending = await asyncio.wait({to_upstream, to_client}, return_when=asyncio.FIRST_EXCEPTION)
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc is not None:
                    raise exc

            try:
                await upstream_ws.send(_build_full_request(EVENT_FINISH_SESSION, {}, session_id=runtime_session_id))
                await upstream_ws.send(_build_full_request(EVENT_FINISH_CONNECTION, {}))
            except WebSocketException:
                pass
    except WebSocketDisconnect:
        return
    except WebSocketException as exc:
        await _safe_send_json(websocket, {"type": "error", "message": f"Upstream websocket error: {exc}"})
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            return
    except Exception as exc:
        await _safe_send_json(websocket, {"type": "error", "message": f"Voice gateway error: {exc}"})
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            return
