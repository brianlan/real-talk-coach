from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.clients.llm import EvaluatorClient, LLMError
from app.config import load_settings
from app.models.evaluation import EvaluationResult, EvaluationScore
from app.telemetry.otel import start_span


@dataclass(frozen=True)
class EvaluationContext:
    session_id: str
    scenario_title: str
    scenario_context: dict[str, Any]
    learning_objectives: list[str]
    evaluation_criteria: list[dict[str, Any]]
    skills_assessed: list[str]
    scoring: dict[str, Any]
    evaluation_instructions: str
    turns: list[dict[str, Any]]


def _format_transcript(turns: list[dict[str, Any]]) -> str:
    lines = []
    for turn in turns:
        speaker = turn.get("speaker", "unknown")
        transcript = turn.get("transcript") or "(transcript pending)"
        lines.append(f"{speaker}: {transcript}")
    return "\n".join(lines)


def _format_evaluation_criteria(evaluation_criteria: list[dict[str, Any]]) -> str:
    lines = []
    for criterion in evaluation_criteria:
        criterion_id = criterion.get("id") or "unknown_criterion"
        description = criterion.get("description") or "No description provided"
        lines.append(f"{criterion_id}: {description}")
    if not lines:
        return "Not provided"
    return "\n".join(lines)


def _format_bullets(items: list[Any]) -> str:
    if not items:
        return "Not provided"
    return "\n".join(f"- {item}" for item in items)


def _format_json_block(value: Any) -> str:
    if not value:
        return "Not provided"
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)


def _parse_tool_call(payload: dict[str, Any]) -> EvaluationResult:
    choices = payload.get("choices", [])
    if not choices:
        raise ValueError("Missing choices in evaluation response")
    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        arguments = tool_calls[0].get("function", {}).get("arguments")
        if not arguments:
            raise ValueError("Missing tool call arguments in evaluation response")
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("Evaluation tool arguments are not valid JSON") from exc
    else:
        content = message.get("content") or ""
        if not content:
            raise ValueError("Missing tool_calls and content in evaluation response")
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Evaluation response missing JSON payload")
        try:
            parsed = json.loads(content[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("Evaluation response content is not valid JSON") from exc
    scores_payload = parsed.get("scores")
    summary = parsed.get("summary")
    if not isinstance(scores_payload, list) or not isinstance(summary, str):
        raise ValueError("Evaluation response missing scores or summary")
    scores: list[EvaluationScore] = []
    for item in scores_payload:
        skill_id = item.get("skillId")
        rating = item.get("rating")
        note = item.get("note")
        if not skill_id or not isinstance(rating, int) or not note:
            raise ValueError("Evaluation score entry invalid")
        if rating < 1 or rating > 5:
            raise ValueError("Evaluation rating out of range")
        scores.append(EvaluationScore(skill_id=skill_id, rating=rating, note=note))
    return EvaluationResult(scores=scores, summary=summary)


async def evaluate_session(context: EvaluationContext) -> EvaluationResult:
    settings = load_settings()
    client = EvaluatorClient(
        base_url=settings.openai_compatible_api_base,
        api_key=settings.openai_compatible_api_key,
        timeout=20.0,
        retries=1,
    )
    transcript = _format_transcript(context.turns)
    evaluation_criteria = _format_evaluation_criteria(context.evaluation_criteria)
    learning_objectives = _format_bullets(context.learning_objectives)
    skills_assessed = _format_bullets(context.skills_assessed)
    scenario_context = _format_json_block(context.scenario_context)
    scoring = _format_json_block(context.scoring)
    evaluation_instructions = context.evaluation_instructions or "Not provided"
    payload = {
        "model": settings.evaluator_model or settings.openai_compatible_api_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You evaluate trainee performance. Use the tool call to return JSON "
                    "with scores and summary. Do not include extra text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Scenario: {context.scenario_title}\n"
                    f"Scenario context:\n{scenario_context}\n"
                    f"Learning objectives:\n{learning_objectives}\n"
                    f"Evaluation criteria (use each criterion id as skillId in scores):\n"
                    f"{evaluation_criteria}\n"
                    f"Skills assessed:\n{skills_assessed}\n"
                    f"Scoring config:\n{scoring}\n"
                    f"Additional evaluation instructions:\n{evaluation_instructions}\n"
                    f"Transcript:\n{transcript}"
                ),
            },
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "evaluation_result",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scores": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "skillId": {"type": "string"},
                                        "rating": {
                                            "type": "integer",
                                            "minimum": 1,
                                            "maximum": 5,
                                        },
                                        "note": {"type": "string"},
                                    },
                                    "required": ["skillId", "rating", "note"],
                                },
                            },
                            "summary": {"type": "string"},
                        },
                        "required": ["scores", "summary"],
                    },
                },
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": "evaluation_result"}},
    }
    try:
        with start_span(
            "evaluation.llm_request",
            {"status": "request", "sessionId": context.session_id},
        ):
            try:
                response = await client.evaluate(payload)
            except LLMError as exc:
                if exc.status_code in {400, 422} and payload.get("tools"):
                    fallback_payload = dict(payload)
                    fallback_payload.pop("tools", None)
                    fallback_payload.pop("tool_choice", None)
                    fallback_messages = [
                        dict(payload["messages"][0]),
                        dict(payload["messages"][1]),
                    ]
                    fallback_messages[0][
                        "content"
                    ] = (
                        "Return only JSON with keys 'scores' and 'summary'. "
                        "Do not include extra text."
                    )
                    fallback_payload["messages"] = fallback_messages
                    response = await client.evaluate(fallback_payload)
                else:
                    raise
        with start_span(
            "evaluation.parse",
            {"status": "parse", "sessionId": context.session_id},
        ):
            return _parse_tool_call(response)
    finally:
        await client.close()
