from __future__ import annotations

import logging
import asyncio
from dataclasses import dataclass
from typing import Any

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class LLMError(Exception):
    message: str
    status_code: int | None = None
    body: str | None = None

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"LLMError(message={self.message!r}, status_code={self.status_code!r})"


def _require_field(payload: dict[str, Any], field: str, context: str) -> None:
    if field not in payload:
        raise LLMError(f"Missing '{field}' in {context} response")


class _BaseLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 60.0,
        retries: int = 0,
        transport: httpx.AsyncBaseTransport | None = None,
        trust_env: bool = True,
    ) -> None:
        self._retries = retries
        self._timeout = timeout
        self._http_client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            trust_env=trust_env,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            http_client=self._http_client,
        )

    async def close(self) -> None:
        await self._client.close()


class EvaluatorClient(_BaseLLMClient):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 60.0,
        retries: int = 0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            retries=retries,
            transport=transport,
            trust_env=False,
        )

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return True
        status_code = getattr(exc, "status_code", None)
        if status_code and status_code >= 500:
            return True
        return False

    def _serialize_tool_call(self, tool_call: Any) -> dict[str, Any]:
        if hasattr(tool_call, "model_dump"):
            return tool_call.model_dump()
        return {
            "id": getattr(tool_call, "id", None),
            "type": getattr(tool_call, "type", None),
            "function": {
                "name": getattr(getattr(tool_call, "function", None), "name", None),
                "arguments": getattr(getattr(tool_call, "function", None), "arguments", None),
            },
        }

    async def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Call evaluator API for evaluation (non-streaming, text only).

        Args:
            payload: Dictionary containing model, messages, and other params

        Returns:
            Dictionary with choices containing message
        """
        for attempt in range(self._retries + 1):
            try:
                response = await self._http_client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json() if response.text else {}
                _require_field(data, "choices", "evaluator")
                choices = data.get("choices", [])
                if not choices:
                    raise LLMError("Missing 'choices' in evaluator response")
                message = choices[0].get("message", {})
                response_message: dict[str, Any] = {"content": message.get("content")}
                tool_calls = message.get("tool_calls") or []
                if tool_calls:
                    response_message["tool_calls"] = tool_calls
                _require_field(
                    {"choices": [{"message": response_message}]},
                    "choices",
                    "evaluator",
                )
                return {"choices": [{"message": response_message}]}
            except Exception as exc:
                if attempt < self._retries and self._should_retry(exc):
                    await asyncio.sleep(0.2 * (attempt + 1))
                    continue
                status_code = getattr(exc, "status_code", None)
                body = getattr(exc, "body", None)
                if isinstance(exc, httpx.HTTPStatusError):
                    status_code = exc.response.status_code
                    body = exc.response.text
                raise LLMError(
                    f"Evaluator failed: {str(exc)}",
                    status_code=status_code,
                    body=body,
                ) from exc
        raise LLMError("Evaluator failed: retries exhausted")
