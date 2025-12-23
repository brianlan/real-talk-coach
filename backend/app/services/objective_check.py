from __future__ import annotations

from dataclasses import dataclass
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
        return ObjectiveCheckResult(status="unknown", reason=None)
    message = choices[0].get("message", {})
    content = (message.get("content") or "").lower()
    if "succeed" in content or "met" in content:
        return ObjectiveCheckResult(status="succeeded", reason=message.get("content"))
    if "fail" in content:
        return ObjectiveCheckResult(status="failed", reason=message.get("content"))
    return ObjectiveCheckResult(status="unknown", reason=message.get("content"))


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
    )
    try:
        payload = {
            "model": settings.objective_check_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an objective checker for coaching sessions.",
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
                        + "\nReturn whether objectives succeeded or failed."
                    ),
                },
            ],
        }
        response = await client.evaluate(payload)
        return _parse_objective_response(response)
    finally:
        await client.close()
