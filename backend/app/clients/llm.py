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
        transport: httpx.BaseTransport | None = None,
        trust_env: bool = True,
    ) -> None:
        self._retries = retries
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


class QwenClient(_BaseLLMClient):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            retries=retries,
            transport=transport,
        )

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code >= 500
        status_code = getattr(exc, "status_code", None)
        if status_code and status_code >= 500:
            return True
        return False

    async def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Call Qwen API for generation (supports streaming).

        Args:
            payload: Dictionary containing model, messages, modalities, audio, stream params

        Returns:
            Dictionary with choices containing message with content and optionally audio
        """
        logger.info(f"QwenClient.generate called with payload keys: {payload.keys()}")
        # Extract parameters from payload
        model = payload.get("model")
        messages = payload.get("messages")
        modalities = payload.get("modalities", ["text"])
        audio_config = payload.get("audio")
        stream = payload.get("stream", False)
        stream_options = payload.get("stream_options")

        logger.info(
            "Model: %s, Modalities: %s, Stream: %s, Audio config: %s",
            model,
            modalities,
            stream,
            audio_config,
        )

        # Build OpenAI client parameters
        client_params = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        # Add modality and audio config if generating audio
        if "audio" in modalities and audio_config:
            client_params["modalities"] = modalities
            client_params["audio"] = audio_config

        # Add stream options if streaming
        if stream and stream_options:
            client_params["stream_options"] = stream_options

        for attempt in range(self._retries + 1):
            try:
                completion = await self._client.chat.completions.create(**client_params)

                # Process the response
                text_parts = []
                audio_parts = []

                if stream:
                    # Stream processing: collect all chunks
                    async for chunk in completion:
                        if chunk.choices:
                            delta = chunk.choices[0].delta

                            # Collect text content
                            if hasattr(delta, "content") and delta.content:
                                text_parts.append(delta.content)

                            # Collect audio data
                            if hasattr(delta, "audio") and delta.audio:
                                audio_data = delta.audio.get("data")
                                if audio_data:
                                    audio_parts.append(audio_data)
                else:
                    # Non-stream processing: single response
                    if completion.choices:
                        message = completion.choices[0].message

                        # Get text content
                        if hasattr(message, "content") and message.content:
                            text_parts.append(message.content)

                        # Get audio data
                        if hasattr(message, "audio") and message.audio:
                            audio_data = message.audio.get("data")
                            if audio_data:
                                audio_parts.append(audio_data)

                # Build response in the format expected by the rest of the codebase
                response_message: dict[str, Any] = {"content": "".join(text_parts)}
                if audio_parts:
                    audio_data = "".join(audio_parts)
                    logger.info(
                        "Collected %s audio chunks, total base64 length: %s",
                        len(audio_parts),
                        len(audio_data),
                    )
                    response_message["audio"] = {"data": audio_data}
                else:
                    logger.warning("No audio parts collected from Qwen response")

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
                    f"Qwen generation failed: {str(exc)}",
                    status_code=status_code,
                    body=body,
                ) from exc

    async def asr(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Call Qwen API for Automatic Speech Recognition.

        Args:
            payload: Dictionary containing model, input (audio data), format, prompt, stream

        Returns:
            Dictionary with transcribed text
        """
        model = payload.get("model")
        audio_base64 = payload.get("input")
        if not model or not audio_base64:
            raise LLMError("Missing 'model' or 'input' for qwen asr")

        audio_format = payload.get("format", "wav")
        prompt = payload.get("prompt", "Do not answer the speaker; output only the verbatim transcript in the original language.")
        stream = payload.get("stream", True)
        stream_options = payload.get("stream_options")

        audio_data_url = f"data:;base64,{audio_base64}"
        messages = [
            {
                "role": "system", 
                "content": "You are a speech-to-text service. Respond only with the transcript."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_data_url, "format": audio_format},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        for attempt in range(self._retries + 1):
            try:
                client_params: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "stream": stream,
                    "modalities": ["text"],
                }
                if stream and stream_options:
                    client_params["stream_options"] = stream_options

                completion = await self._client.chat.completions.create(**client_params)

                text_parts: list[str] = []
                if stream:
                    async for chunk in completion:
                        if chunk.choices:
                            delta = chunk.choices[0].delta
                            if hasattr(delta, "content") and delta.content:
                                text_parts.append(delta.content)
                else:
                    if completion.choices:
                        message = completion.choices[0].message
                        if hasattr(message, "content") and message.content:
                            text_parts.append(message.content)

                text = "".join(text_parts)
                if not text:
                    raise LLMError("Missing 'text' in qwen asr response")
                return {"text": text}
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
                    f"Qwen ASR failed: {str(exc)}",
                    status_code=status_code,
                    body=body,
                ) from exc


class EvaluatorClient(_BaseLLMClient):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 60.0,
        retries: int = 0,
        transport: httpx.BaseTransport | None = None,
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
