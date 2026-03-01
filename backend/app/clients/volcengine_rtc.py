from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote
from urllib.parse import urlparse

import httpx


def _base64url(data: bytes) -> str:
    return __import__("base64").urlsafe_b64encode(data).decode("utf-8").rstrip("=")


@dataclass
class VolcengineRTCError(Exception):
    message: str
    status_code: int | None = None
    body: str | None = None

    def __str__(self) -> str:
        return self.message


class VolcengineAuthError(VolcengineRTCError):
    pass


class VolcengineAPIError(VolcengineRTCError):
    pass


class VolcengineRTCClient:
    def __init__(
        self,
        *,
        access_key_id: str,
        secret_access_key: str,
        app_id: str,
        app_key: str,
        voice_chat_endpoint: str,
        voice_model_id: str,
        region: str = "cn-north-1",
        service: str = "rtc",
        api_version: str = "2024-01-01",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._access_key_id = access_key_id.strip()
        self._secret_access_key = secret_access_key.strip()
        self._app_id = app_id.strip()
        self._app_key = app_key.strip()
        self._voice_model_id = voice_model_id.strip()
        self._region = region
        self._service = service
        self._api_version = api_version

        if not self._access_key_id or not self._secret_access_key:
            raise VolcengineAuthError("Volcengine credentials are required")
        if not self._app_id or not self._app_key:
            raise VolcengineAuthError("Volcengine RTC app_id/app_key are required")

        parsed = urlparse(voice_chat_endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise VolcengineRTCError(
                f"Invalid Volcengine voice chat endpoint: {voice_chat_endpoint}"
            )
        self._host = parsed.netloc
        self._base_path = parsed.path or "/"

        self._http_client = httpx.AsyncClient(
            base_url=f"{parsed.scheme}://{parsed.netloc}",
            timeout=timeout,
            transport=transport,
            trust_env=False,
        )

    async def close(self) -> None:
        await self._http_client.aclose()

    def generate_rtc_token(self, room_id: str, user_id: str) -> str:
        room_id = room_id.strip()
        user_id = user_id.strip()
        if not room_id:
            raise VolcengineRTCError("room_id must not be empty")
        if not user_id:
            raise VolcengineRTCError("user_id must not be empty")

        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "app_id": self._app_id,
            "room_id": room_id,
            "user_id": user_id,
            "version": 1,
            "iat": now,
            "exp": now + 3600,
            "privileges": {
                "join_room": True,
                "publish_audio": True,
                "subscribe_audio": True,
            },
        }
        header_b64 = _base64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _base64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(
            self._app_key.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        return f"{header_b64}.{payload_b64}.{_base64url(signature)}"

    def _sign_v4(self, request: dict[str, Any]) -> dict[str, Any]:
        method = str(request.get("method", "POST")).upper()
        path = str(request.get("path", self._base_path)) or "/"
        query = request.get("query") or {}
        body = request.get("body", "")
        region = str(request.get("region", self._region))
        service = str(request.get("service", self._service))

        if isinstance(body, str):
            body_bytes = body.encode("utf-8")
        else:
            body_bytes = body

        timestamp = str(request.get("timestamp") or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
        date_stamp = timestamp[:8]
        payload_hash = hashlib.sha256(body_bytes).hexdigest()

        headers = {str(k).lower(): str(v).strip() for k, v in (request.get("headers") or {}).items()}
        headers.setdefault("host", self._host)
        headers["x-date"] = timestamp
        headers["x-content-sha256"] = payload_hash
        headers.setdefault("content-type", "application/json")

        sorted_header_keys = sorted(headers.keys())
        canonical_headers = "".join(f"{key}:{headers[key]}\n" for key in sorted_header_keys)
        signed_headers = ";".join(sorted_header_keys)

        canonical_query = "&".join(
            f"{quote(str(key), safe='-_.~')}={quote(str(query[key]), safe='-_.~')}"
            for key in sorted(query.keys())
        )
        canonical_request = "\n".join(
            [method, path, canonical_query, canonical_headers, signed_headers, payload_hash]
        )
        credential_scope = f"{date_stamp}/{region}/{service}/request"
        string_to_sign = "\n".join(
            [
                "HMAC-SHA256",
                timestamp,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )

        k_date = hmac.new(self._secret_access_key.encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region.encode("utf-8"), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service.encode("utf-8"), hashlib.sha256).digest()
        signing_key = hmac.new(k_service, b"request", hashlib.sha256).digest()
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization = (
            "HMAC-SHA256 "
            f"Credential={self._access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        signed_request_headers = dict(headers)
        signed_request_headers["authorization"] = authorization

        return {
            "headers": signed_request_headers,
            "canonical_request": canonical_request,
            "string_to_sign": string_to_sign,
            "signature": signature,
            "credential_scope": credential_scope,
        }

    async def start_voice_chat(self, room_id: str, task_id: str, system_prompt: str) -> dict[str, Any]:
        payload = {
            "AppId": self._app_id,
            "RoomId": room_id,
            "TaskId": task_id,
            "Config": {
                "SystemPrompt": system_prompt,
                "ModelId": self._voice_model_id,
            },
        }
        return await self._call_voice_api("StartVoiceChat", payload)

    async def stop_voice_chat(self, room_id: str, task_id: str) -> dict[str, Any]:
        payload = {
            "AppId": self._app_id,
            "RoomId": room_id,
            "TaskId": task_id,
        }
        return await self._call_voice_api("StopVoiceChat", payload)

    async def _call_voice_api(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"))
        query = {"Action": action, "Version": self._api_version}
        signed = self._sign_v4(
            {
                "method": "POST",
                "path": self._base_path,
                "query": query,
                "body": body,
            }
        )
        try:
            response = await self._http_client.post(
                self._base_path,
                params=query,
                content=body,
                headers=signed["headers"],
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise VolcengineAPIError(
                f"{action} failed with HTTP {exc.response.status_code}",
                status_code=exc.response.status_code,
                body=exc.response.text,
            ) from exc
        except httpx.HTTPError as exc:
            raise VolcengineAPIError(f"{action} request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise VolcengineAPIError(f"{action} returned non-JSON response") from exc

        error = (data.get("ResponseMetadata") or {}).get("Error")
        if error:
            code = error.get("Code", "UnknownError")
            message = error.get("Message", "Unknown error")
            raise VolcengineAPIError(f"{action} failed: {code} - {message}")

        return data
