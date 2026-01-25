from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.clients.llm import EvaluatorClient, LLMError
from app.config import load_settings
from app.telemetry.otel import start_span

logger = logging.getLogger(__name__)


def _language_label(language: str) -> str:
    return "Simplified Chinese" if language == "zh" else "English"


def _build_blueprint(scenario: Any, language: str) -> str:
    ai_persona = getattr(scenario, "ai_persona", {}) or {}
    trainee_persona = getattr(scenario, "trainee_persona", {}) or {}
    title = getattr(scenario, "title", "") or ""
    description = getattr(scenario, "description", "") or ""
    objective = getattr(scenario, "objective", "") or ""
    end_criteria = getattr(scenario, "end_criteria", []) or []

    end_criteria_text = "\n".join(f"- {item}" for item in end_criteria) or "Not provided"

    return (
        f"Language: {_language_label(language)}\n"
        f"AI persona: {ai_persona.get('name', '')} ({ai_persona.get('role', '')}). Background: {ai_persona.get('background', '')}\n"
        f"Trainee persona: {trainee_persona.get('name', '')} ({trainee_persona.get('role', '')}). Background: {trainee_persona.get('background', '')}\n"
        f"Scenario title: {title}\n"
        f"Scenario description: {description}\n"
        f"Objective: {objective}\n"
        f"End criteria:\n{end_criteria_text}\n"
    )


def _build_messages(
    scenario: Any, language: str, *, strict: bool = False
) -> list[dict[str, str]]:
    blueprint = _build_blueprint(scenario, language)
    ai_persona = getattr(scenario, "ai_persona", {}) or {}
    trainee_persona = getattr(scenario, "trainee_persona", {}) or {}
    ai_name = ai_persona.get("name", "") or "the AI persona"
    trainee_name = trainee_persona.get("name", "") or "the trainee persona"
    strict_lines = ""
    if strict:
        strict_lines = (
            f"Critical constraints:\\n"
            f"- The AI must speak as {ai_name}.\\n"
            f"- Never instruct the model to speak as {trainee_name}.\\n"
            f"- Do not write prompts like 'You are {trainee_name}'.\\n"
            f"- If you mention a persona name, only mention {ai_name}.\\n"
        )
    return [
        {
            "role": "system",
            "content": (
                "You are a prompt designer for a roleplay AI. "
                "Create a single concise user prompt that will be given to a roleplay model "
                "to generate the FIRST spoken line. Output only the prompt text. "
                "No quotes, no markdown, no JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{blueprint}\n"
                "Requirements:\n"
                "- Use the specified language only.\n"
                "- Keep it short (1-3 sentences).\n"
                f"- Instruct the AI to open the conversation in-character as {ai_name}.\n"
                "- Specify a calm, professional tone consistent with the persona.\n"
                "- Ask a question or invite a response.\n"
                f"- Do not instruct the model to speak as {trainee_name}.\n"
                f"{strict_lines}"
                "Return ONLY the prompt text."
            ),
        },
    ]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_contradicting_prompt(
    prompt: str, *, ai_name: str, trainee_name: str
) -> bool:
    if not prompt:
        return True
    lowered = prompt.lower()
    if trainee_name:
        escaped = re.escape(trainee_name)
        role_patterns = [
            rf"你是{escaped}",
            rf"作为{escaped}",
            rf"扮演{escaped}",
            rf"act as {escaped.lower()}",
            rf"you are {escaped.lower()}",
            rf"speak as {escaped.lower()}",
            rf"start as {escaped.lower()}",
        ]
        for pattern in role_patterns:
            if re.search(pattern, lowered):
                return True
    if ai_name and ai_name.lower() not in lowered:
        return True
    return False


async def generate_opening_prompt(*, scenario: Any, language: str) -> tuple[str, str, str, str]:
    settings = load_settings()
    logger.info("Opening prompt generation requested (language=%s)", language)
    ai_persona = getattr(scenario, "ai_persona", {}) or {}
    trainee_persona = getattr(scenario, "trainee_persona", {}) or {}
    ai_name = ai_persona.get("name", "") or ""
    trainee_name = trainee_persona.get("name", "") or ""
    client = EvaluatorClient(
        base_url=settings.chatai_api_base,
        api_key=settings.chatai_api_key,
        timeout=20.0,
        retries=1,
    )
    try:
        for attempt in range(2):
            messages = _build_messages(scenario, language, strict=attempt == 1)
            payload = {
                "model": settings.chatai_api_model,
                "messages": messages,
                "temperature": 0.3,
            }
            with start_span(
                "opening_prompt.generate",
                {"language": language, "attempt": attempt + 1},
            ):
                response = await client.evaluate(payload)
            choices = response.get("choices", [])
            if not choices:
                raise LLMError("Missing choices in opening prompt response")
            message = choices[0].get("message", {})
            content = (message.get("content") or "").strip()
            if not content:
                raise LLMError("Opening prompt response missing content")
            if _is_contradicting_prompt(
                content, ai_name=ai_name, trainee_name=trainee_name
            ):
                logger.warning(
                    "Opening prompt contradicts persona constraints; retrying (attempt %s)",
                    attempt + 1,
                )
                continue
            logger.info("Opening prompt generated (%s chars)", len(content))
            return content, settings.chatai_api_model, "chatai", _now_iso()
    finally:
        await client.close()
    raise LLMError("Opening prompt failed validation after retries")
