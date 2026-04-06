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


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _scenario_dict(scenario: Any, snake_name: str, camel_name: str) -> dict[str, Any]:
    return _as_dict(getattr(scenario, snake_name, None) or getattr(scenario, camel_name, None))


def _scenario_personas(scenario: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    simulation_config = _scenario_dict(scenario, "simulation_config", "simulationConfig")
    return _as_dict(simulation_config.get("ai")), _as_dict(simulation_config.get("trainee"))


def _scenario_title(scenario: Any) -> str:
    metadata = _scenario_dict(scenario, "metadata", "metadata")
    return str(metadata.get("title") or "").strip()


def _scenario_description(scenario: Any) -> str:
    metadata = _scenario_dict(scenario, "metadata", "metadata")
    context = _scenario_dict(scenario, "context", "context")
    description = str(metadata.get("description") or "").strip()
    if description:
        return description
    return str(context.get("situation") or "").strip()


def _learning_objectives_text(scenario: Any) -> str:
    evaluation_config = _scenario_dict(scenario, "evaluation_config", "evaluationConfig")
    objectives = _text_list(evaluation_config.get("learningObjectives"))
    return "\n".join(f"- {item}" for item in objectives) or "Not provided"


def _end_states_text(scenario: Any) -> str:
    simulation_config = _scenario_dict(scenario, "simulation_config", "simulationConfig")
    end_conditions = _as_dict(simulation_config.get("conversationEndConditions"))
    end_states = _text_list(end_conditions.get("possibleEndStates"))
    return "\n".join(f"- {item}" for item in end_states) or "Not provided"


def _build_blueprint(scenario: Any, language: str) -> str:
    ai_persona, trainee_persona = _scenario_personas(scenario)
    title = _scenario_title(scenario)
    description = _scenario_description(scenario)
    context = _scenario_dict(scenario, "context", "context")

    return (
        f"Language: {_language_label(language)}\n"
        f"AI persona: {ai_persona.get('name', '')} ({ai_persona.get('role', '')}). Background: {ai_persona.get('background', '')}\n"
        f"Trainee persona: {trainee_persona.get('name', '')} ({trainee_persona.get('role', '')}). Background: {trainee_persona.get('background', '')}\n"
        f"Scenario title: {title}\n"
        f"Scenario description: {description}\n"
        f"Context background: {context.get('background', '')}\n"
        f"Conversation setting: {context.get('setting', '')}\n"
        f"Learning objectives:\n{_learning_objectives_text(scenario)}\n"
        f"Possible end states:\n{_end_states_text(scenario)}\n"
    )


def _build_messages(
    scenario: Any, language: str, *, strict: bool = False
) -> list[dict[str, str]]:
    blueprint = _build_blueprint(scenario, language)
    ai_persona, trainee_persona = _scenario_personas(scenario)
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
    ai_persona, trainee_persona = _scenario_personas(scenario)
    ai_name = ai_persona.get("name", "") or ""
    trainee_name = trainee_persona.get("name", "") or ""
    client = EvaluatorClient(
        base_url=settings.openai_compatible_api_base,
        api_key=settings.openai_compatible_api_key,
        timeout=20.0,
        retries=1,
    )
    try:
        for attempt in range(2):
            messages = _build_messages(scenario, language, strict=attempt == 1)
            payload = {
                "model": settings.openai_compatible_api_model,
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
            return content, settings.openai_compatible_api_model, "openai_compatible", _now_iso()
    finally:
        await client.close()
    raise LLMError("Opening prompt failed validation after retries")
