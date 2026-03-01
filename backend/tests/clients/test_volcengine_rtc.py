# pyright: reportMissingImports=false

import base64
import hashlib
import hmac
import json

import httpx
import pytest

from app.clients.volcengine_rtc import VolcengineAPIError
from app.clients.volcengine_rtc import VolcengineRTCClient
from app.clients.volcengine_rtc import VolcengineRTCError


def _decode_b64url(value: str) -> dict:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return json.loads(base64.urlsafe_b64decode(value + padding))


def _build_client(*, transport: httpx.AsyncBaseTransport | None = None) -> VolcengineRTCClient:
    return VolcengineRTCClient(
        access_key_id="ak-test",
        secret_access_key="sk-test",
        app_id="app-test",
        app_key="app-key-test",
        voice_chat_endpoint="https://rtc.volcengineapi.com",
        voice_model_id="doubao-voice-realtime",
        transport=transport,
    )


def test_generate_rtc_token_has_jwt_structure_and_claims():
    client = _build_client()

    token = client.generate_rtc_token("room-1", "user-1")
    header_b64, payload_b64, signature_b64 = token.split(".")
    header = _decode_b64url(header_b64)
    payload = _decode_b64url(payload_b64)

    assert header == {"alg": "HS256", "typ": "JWT"}
    assert payload["app_id"] == "app-test"
    assert payload["room_id"] == "room-1"
    assert payload["user_id"] == "user-1"
    assert payload["exp"] > payload["iat"]
    assert payload["privileges"]["join_room"] is True
    assert signature_b64


def test_generate_rtc_token_requires_non_empty_ids():
    client = _build_client()

    with pytest.raises(VolcengineRTCError):
        client.generate_rtc_token("", "user-1")

    with pytest.raises(VolcengineRTCError):
        client.generate_rtc_token("room-1", "")


def test_sign_v4_produces_expected_authorization_format():
    client = _build_client()
    body = json.dumps({"AppId": "app-test", "TaskId": "task-1"}, separators=(",", ":"))
    signed = client._sign_v4(
        {
            "method": "POST",
            "path": "/",
            "query": {"Action": "StartVoiceChat", "Version": "2024-01-01"},
            "body": body,
            "headers": {"x-custom": "abc"},
            "timestamp": "20260301T120000Z",
            "region": "cn-north-1",
            "service": "rtc",
        }
    )

    auth = signed["headers"]["authorization"]
    assert auth.startswith("HMAC-SHA256 Credential=ak-test/20260301/cn-north-1/rtc/request")
    assert "SignedHeaders=" in auth
    assert "Signature=" in auth
    assert signed["headers"]["x-content-sha256"] == hashlib.sha256(body.encode("utf-8")).hexdigest()


def test_sign_v4_signature_is_deterministic():
    client = _build_client()
    body = "{}"
    signed = client._sign_v4(
        {
            "method": "POST",
            "path": "/",
            "query": {"Action": "StopVoiceChat", "Version": "2024-01-01"},
            "body": body,
            "timestamp": "20260301T120000Z",
            "region": "cn-north-1",
            "service": "rtc",
        }
    )

    date_key = hmac.new(b"sk-test", b"20260301", hashlib.sha256).digest()
    region_key = hmac.new(date_key, b"cn-north-1", hashlib.sha256).digest()
    service_key = hmac.new(region_key, b"rtc", hashlib.sha256).digest()
    signing_key = hmac.new(service_key, b"request", hashlib.sha256).digest()
    expected_signature = hmac.new(
        signing_key,
        signed["string_to_sign"].encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert signed["signature"] == expected_signature


@pytest.mark.asyncio
async def test_start_voice_chat_calls_api_and_returns_data():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["Action"] == "StartVoiceChat"
        assert request.headers["authorization"].startswith("HMAC-SHA256 ")
        payload = json.loads(request.content)
        assert payload["RoomId"] == "room-1"
        assert payload["TaskId"] == "task-1"
        assert payload["Config"]["SystemPrompt"] == "Prompt"
        return httpx.Response(200, json={"Result": {"TaskState": "started"}})

    client = _build_client(transport=httpx.MockTransport(handler))
    try:
        result = await client.start_voice_chat("room-1", "task-1", "Prompt")
    finally:
        await client.close()

    assert result["Result"]["TaskState"] == "started"


@pytest.mark.asyncio
async def test_stop_voice_chat_raises_on_http_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    client = _build_client(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(VolcengineAPIError) as exc:
            await client.stop_voice_chat("room-1", "task-1")
    finally:
        await client.close()

    assert exc.value.status_code == 403
    assert "StopVoiceChat failed with HTTP 403" in str(exc.value)


@pytest.mark.asyncio
async def test_start_voice_chat_raises_on_api_error_payload():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ResponseMetadata": {
                    "Error": {
                        "Code": "InvalidParameter",
                        "Message": "TaskId duplicated",
                    }
                }
            },
        )

    client = _build_client(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(VolcengineAPIError) as exc:
            await client.start_voice_chat("room-1", "task-1", "Prompt")
    finally:
        await client.close()

    assert "InvalidParameter" in str(exc.value)
