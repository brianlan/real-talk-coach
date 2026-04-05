from __future__ import annotations

from typing import Any

FALLBACK_SYSTEM_PROMPT = (
    "You are an AI communication coach helping the user practice difficult conversations."
)
FALLBACK_BOT_NAME = "Real Talk Coach"
ENGLISH_GREETING = "Hey, what's up?"
CHINESE_GREETING = "嘿，有什么事吗？"


def _persona_block(persona: dict[str, Any] | None, label: str) -> str:
    if not persona:
        return f"{label}: (not provided)"
    name = persona.get("name") or "Unknown"
    role = persona.get("role") or "Unknown"
    background = persona.get("background") or "Not provided"
    return f"{label}: {name} ({role}). Background: {background}"


def _language_label(language: str) -> str:
    return "Simplified Chinese" if language == "zh" else "English"


def _end_criteria_lines(end_criteria: list[str] | None) -> list[str]:
    items = end_criteria or []
    if not items:
        return ["End criteria:", "- Not provided"]
    return ["End criteria:", *(f"- {item}" for item in items)]


def _greeting_for_language(language: str) -> str:
    return CHINESE_GREETING if language == "zh" else ENGLISH_GREETING


def build_e2e_system_prompt(scenario: Any, language: str) -> str:
    if scenario is None:
        return FALLBACK_SYSTEM_PROMPT

    title = getattr(scenario, "title", "") or ""
    description = getattr(scenario, "description", "") or ""
    objective = getattr(scenario, "objective", "") or ""
    prompt = getattr(scenario, "prompt", "") or ""
    end_criteria = getattr(scenario, "end_criteria", None) or getattr(
        scenario, "endCriteria", []
    )
    ai_persona = getattr(scenario, "ai_persona", None) or getattr(
        scenario, "aiPersona", None
    )
    trainee_persona = getattr(scenario, "trainee_persona", None) or getattr(
        scenario, "traineePersona", None
    )

    system_lines = [
        "You are the AI roleplayer for a practice conversation.",
        _persona_block(ai_persona, "Your persona"),
        _persona_block(trainee_persona, "Trainee persona"),
    ]
    if title:
        system_lines.append(f"Scenario title: {title}")
    if description:
        system_lines.append(f"Scenario description: {description}")
    if objective:
        system_lines.append(f"Objective: {objective}")
    system_lines.extend(_end_criteria_lines(end_criteria))
    if prompt:
        system_lines.append(f"Additional instructions: {prompt}")
    system_lines.append(f"Use {_language_label(language)} for all responses.")
    system_lines.append("Stay in character and respond naturally to the trainee.")
    return "\n".join(system_lines)


def resolve_opening_content(
    scenario: Any, language: str, who_talks_first: str | None
) -> tuple[str, bool]:
    if scenario is None:
        return _greeting_for_language(language), False

    normalized = who_talks_first if who_talks_first in {"ai", "trainee"} else "ai"
    if normalized == "trainee":
        return _greeting_for_language(language), False
    return "", True


def resolve_bot_name(scenario: Any) -> str:
    if scenario is None:
        return FALLBACK_BOT_NAME
    ai_persona = getattr(scenario, "ai_persona", None) or getattr(
        scenario, "aiPersona", None
    )
    name = (ai_persona or {}).get("name") or ""
    return name or FALLBACK_BOT_NAME
