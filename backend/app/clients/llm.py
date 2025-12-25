from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


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
        timeout: float = 60.0,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.close()


class QwenClient(_BaseLLMClient):
    async def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Call Qwen API for generation (supports streaming).

        Args:
            payload: Dictionary containing model, messages, modalities, audio, stream params

        Returns:
            Dictionary with choices containing message with content and optionally audio
        """
        try:
            logger.info(f"QwenClient.generate called with payload keys: {payload.keys()}")
            # Extract parameters from payload
            model = payload.get("model")
            messages = payload.get("messages")
            modalities = payload.get("modalities", ["text"])
            audio_config = payload.get("audio")
            stream = payload.get("stream", False)
            stream_options = payload.get("stream_options")

            logger.info(f"Model: {model}, Modalities: {modalities}, Stream: {stream}, Audio config: {audio_config}")

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

            # Make the API call
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
                response_message["audio"] = {"data": "".join(audio_parts)}

            return {"choices": [{"message": response_message}]}

        except Exception as exc:
            raise LLMError(f"Qwen generation failed: {str(exc)}") from exc

    async def asr(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Call Qwen API for Automatic Speech Recognition.

        Args:
            payload: Dictionary containing model and input (audio data)

        Returns:
            Dictionary with transcribed text
        """
        try:
            response = await self._client.audio.transcriptions.create(**payload)
            _require_field({"text": response.text}, "text", "qwen asr")
            return {"text": response.text}
        except Exception as exc:
            raise LLMError(f"Qwen ASR failed: {str(exc)}") from exc


class EvaluatorClient(_BaseLLMClient):
    async def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Call evaluator API for evaluation (non-streaming, text only).

        Args:
            payload: Dictionary containing model, messages, and other params

        Returns:
            Dictionary with choices containing message
        """
        try:
            completion = await self._client.chat.completions.create(**payload)
            _require_field(
                {"choices": [{"message": {"content": completion.choices[0].message.content}}]},
                "choices",
                "evaluator",
            )
            return {"choices": [{"message": {"content": completion.choices[0].message.content}}]}
        except Exception as exc:
            raise LLMError(f"Evaluator failed: {str(exc)}") from exc
