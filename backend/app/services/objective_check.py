from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from app.clients.llm import EvaluatorClient
from app.config import load_settings


@dataclass(frozen=True)
class ObjectiveCheckResult:
    status: str
    reason: str | None


def _parse_objective_response(payload: dict[str, Any]) -> ObjectiveCheckResult:
    choices = payload.get("choices", [])
    if not choices:
        return ObjectiveCheckResult(status="continue", reason=None)
    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        arguments = tool_calls[0].get("function", {}).get("arguments")
        if arguments:
            try:
                parsed = json.loads(arguments)
            except json.JSONDecodeError:
                return ObjectiveCheckResult(status="continue", reason=None)
            status = parsed.get("status")
            reason = parsed.get("reason")
            if status in {"continue", "succeeded", "failed"}:
                return ObjectiveCheckResult(status=status, reason=reason)
    return ObjectiveCheckResult(status="continue", reason=message.get("content"))


async def run_objective_check(
    *,
    scenario_objective: str,
    transcript: str,
    end_criteria: list[str],
) -> ObjectiveCheckResult:
    settings = load_settings()
    client = EvaluatorClient(
        base_url=settings.objective_check_api_base,
        api_key=settings.objective_check_api_key,
        timeout=4.0,
    )
    try:
        payload = {
            "model": settings.objective_check_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You assess whether the trainee achieved the objective. "
                        "Return a tool call with status=continue|succeeded|failed."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Objective: "
                        + scenario_objective
                        + "\nEnd criteria: "
                        + ", ".join(end_criteria)
                        + "\nTranscript: "
                        + transcript
                    ),
                },
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "objective_check_result",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "status": {
                                    "type": "string",
                                    "enum": ["continue", "succeeded", "failed"],
                                },
                                "reason": {"type": "string"},
                            },
                            "required": ["status"],
                        },
                    },
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {"name": "objective_check_result"},
            },
        }
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = await client.evaluate(payload)
                return _parse_objective_response(response)
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    continue
                return ObjectiveCheckResult(status="continue", reason=str(last_error))
        return ObjectiveCheckResult(status="continue", reason=None)
    finally:
        await client.close()
