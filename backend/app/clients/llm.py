from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class LLMError(Exception):
    message: str
    status_code: int | None = None
    body: str | None = None

    def __str__(self) -> str:
        return self.message


def _require_field(payload: dict[str, Any], field: str, context: str) -> None:
    if field not in payload:
        raise LLMError(f"Missing '{field}' in {context} response")


class _BaseLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 10.0,
        retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._retries = retries
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.RequestError as exc:
                last_error = exc
            else:
                if response.status_code >= 500:
                    last_error = LLMError(
                        f"LLM error {response.status_code}",
                        status_code=response.status_code,
                        body=response.text,
                    )
                else:
                    return response
            if attempt < self._retries:
                continue
        raise LLMError("LLM request failed") from last_error

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._request(method, path, **kwargs)
        if not response.is_success:
            raise LLMError(
                f"LLM error {response.status_code}: {response.text}",
                status_code=response.status_code,
                body=response.text,
            )
        return response.json()


class QwenClient(_BaseLLMClient):
    async def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request_json("POST", "/chat/completions", json=payload)
        _require_field(response, "choices", "qwen generation")
        return response

    async def asr(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request_json("POST", "/audio/transcriptions", json=payload)
        _require_field(response, "text", "qwen asr")
        return response


class EvaluatorClient(_BaseLLMClient):
    async def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request_json("POST", "/chat/completions", json=payload)
        _require_field(response, "choices", "evaluator")
        return response
