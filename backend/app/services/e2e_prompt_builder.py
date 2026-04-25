from __future__ import annotations

import json
from typing import Any

FALLBACK_SYSTEM_PROMPT = (
    "You are an AI communication coach helping the user practice difficult conversations."
)
FALLBACK_BOT_NAME = "Real Talk Coach"
ENGLISH_GREETING = "Hey, what's up?"
CHINESE_GREETING = "嘿，有什么事吗？"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _scenario_dict(scenario: Any, snake_name: str, camel_name: str) -> dict[str, Any]:
    return _as_dict(getattr(scenario, snake_name, None) or getattr(scenario, camel_name, None))


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _section(title: str, lines: list[str]) -> str:
    return "\n".join([title, *lines])


def _bullet_block(title: str, items: Any, empty_text: str = "Not provided") -> list[str]:
    values = _text_list(items)
    if not values:
        return [f"{title}: {empty_text}"]
    return [f"{title}:", *(f"- {value}" for value in values)]


def _conversation_language(scenario: Any, language: str) -> str:
    simulation_config = _scenario_dict(scenario, "simulation_config", "simulationConfig")
    configured = str(simulation_config.get("language") or "").strip().lower()
    if language == "zh":
        return "Chinese"
    if configured in {"zh", "chinese", "simplified chinese"}:
        return "Chinese"
    return "English"


def _normalize_conversation_start_role(speaker_role_id: Any) -> str | None:
    value = str(speaker_role_id or "").strip().lower()
    if not value:
        return None
    if value in {"ai", "assistant", "bot", "coach", "manager"}:
        return "ai"
    if value in {"trainee", "employee", "user", "learner", "candidate"}:
        return "trainee"
    return None


def _greeting_for_language(language: str) -> str:
    return CHINESE_GREETING if language == "zh" else ENGLISH_GREETING


def _format_list(items: Any, empty_text: str = "Not provided") -> list[str]:
    values = _text_list(items)
    if not values:
        return [empty_text]
    return [f"• {value}" for value in values]


def _normalize_json_content(value: Any) -> Any | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, dict):
        normalized = {
            str(key).strip() or str(key): normalized_value
            for key, item in value.items()
            if (normalized_value := _normalize_json_content(item)) is not None
        }
        return normalized or None
    if isinstance(value, list):
        normalized = [
            normalized_item
            for item in value
            if (normalized_item := _normalize_json_content(item)) is not None
        ]
        return normalized or None
    return value


def _json_scalar_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _json_bullet_lines(value: Any, *, indent: int = 0, label: str | None = None) -> list[str]:
    prefix = "  " * indent
    bullet = f"{prefix}•"

    if isinstance(value, dict):
        lines: list[str] = []
        if label is not None:
            lines.append(f"{bullet} {label}:")
            indent += 1
            prefix = "  " * indent
            bullet = f"{prefix}•"
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.extend(_json_bullet_lines(item, indent=indent, label=key))
            else:
                lines.append(f"{bullet} {key}: {_json_scalar_text(item)}")
        return lines

    if isinstance(value, list):
        lines: list[str] = []
        if label is not None:
            lines.append(f"{bullet} {label}:")
            indent += 1
            prefix = "  " * indent
            bullet = f"{prefix}•"
        for item in value:
            if isinstance(item, (dict, list)):
                nested_lines = _json_bullet_lines(item, indent=indent)
                if nested_lines:
                    lines.extend(nested_lines)
            else:
                lines.append(f"{bullet} {_json_scalar_text(item)}")
        return lines

    text = _json_scalar_text(value)
    if label is not None:
        return [f"{bullet} {label}: {text}"]
    return [f"{bullet} {text}"]


def _decision_constraint_lines(decision_constraints: Any) -> list[str]:
    normalized = _normalize_json_content(decision_constraints)
    if normalized is None:
        return []
    return _json_bullet_lines(normalized)


def _start_of_simulation_lines(conversation_start: dict[str, Any]) -> list[str]:
    starter = _normalize_conversation_start_role(conversation_start.get("speakerRoleId"))
    if starter == "ai":
        return [
            "You will begin the conversation.",
            "Start naturally as your character.",
        ]
    return [
        "The trainee will begin the conversation.",
        "Wait for the trainee's first message and respond naturally as your character.",
    ]


def build_e2e_system_prompt(scenario: Any, language: str) -> str:
    if scenario is None:
        return FALLBACK_SYSTEM_PROMPT

    context = _scenario_dict(scenario, "context", "context")
    simulation_config = _scenario_dict(scenario, "simulation_config", "simulationConfig")
    ai_persona = _as_dict(simulation_config.get("ai"))
    trainee_persona = _as_dict(simulation_config.get("trainee"))
    conversation_dynamics = _as_dict(simulation_config.get("conversationDynamics"))
    decision_constraints = simulation_config.get("decisionConstraints")
    end_conditions = _as_dict(simulation_config.get("conversationEndConditions"))
    conversation_start = _as_dict(simulation_config.get("conversationStart"))

    decision_constraint_lines = _decision_constraint_lines(decision_constraints)

    realistic_behavior_lines = [
        "",
        "Behave like a realistic person in this situation.",
        "",
        "Typical behaviors may include:",
        *_format_list(conversation_dynamics.get("typicalBehaviors")),
        "",
        "Possible responses may include:",
        *_format_list(conversation_dynamics.get("possibleResponses")),
        "",
    ]
    if decision_constraint_lines:
        realistic_behavior_lines.extend(
            [
                "Keep the following constraints in mind:",
                *decision_constraint_lines,
                "",
            ]
        )
    realistic_behavior_lines.extend(
        [
            "Do NOT immediately agree with the trainee's request unless sufficient justification is provided.",
            "",
            "---",
        ]
    )

    sections = [
        "\n".join(
            [
                "You are running a conversation practice simulation.",
                "",
                "Your job is to roleplay a character in a realistic conversation so that the trainee can practice communication skills.",
                "",
                "Follow the instructions carefully.",
                "",
                "---",
            ]
        ),
        _section(
            "## ROLE YOU ARE PLAYING",
            [
                "",
                "You are:",
                "",
                f"Name: {ai_persona.get('name') or 'Unknown'}",
                f"Role: {ai_persona.get('role') or 'Unknown'}",
                "",
                "Personality traits:",
                *_format_list(ai_persona.get("personality")),
                "",
                "Motivations:",
                *_format_list(ai_persona.get("motivations")),
                "",
                "Constraints:",
                *_format_list(ai_persona.get("constraints")),
                "",
                "Behavior tendencies:",
                *_format_list(ai_persona.get("tendencies")),
                "",
                "Current emotional state:",
                ai_persona.get("emotionalState") or "Not provided",
                "",
                "---",
            ],
        ),
        _section(
            "## SCENARIO CONTEXT",
            [
                "",
                f"Situation: {context.get('situation') or 'Not provided'}",
                "",
                f"Background: {context.get('background') or 'Not provided'}",
                "",
                f"Conversation setting: {context.get('setting') or 'Not provided'}",
                "",
                "---",
            ],
        ),
        _section(
            "## TRAINEE ROLE (FOR CONTEXT ONLY)",
            [
                "",
                "The trainee is roleplaying:",
                "",
                f"Name: {trainee_persona.get('name') or 'Unknown'}",
                f"Role: {trainee_persona.get('role') or 'Unknown'}",
                "",
                "Their situation:",
                *_format_list(trainee_persona.get("knowledge")),
                "",
                "Their mindset may include:",
                trainee_persona.get("emotionalState") or "Not provided",
                "",
                "Do NOT help the trainee succeed.",
                "Only respond as the character would naturally respond.",
                "",
                "---",
            ],
        ),
        _section(
            "## ROLEPLAY RULES",
            [
                "",
                "Stay fully in character.",
                "",
                "Never narrate actions, stage directions, or internal thoughts.",
                "",
                "Do NOT describe the scenario.",
                "",
                "Do NOT give advice, coaching, or feedback.",
                "",
                "Do NOT mention evaluation criteria or training mechanics.",
                "",
                "Only speak as the character in the conversation.",
                "",
                "---",
            ],
        ),
        _section(
            "## CONVERSATION STYLE",
            [
                "",
                "Follow these guidelines:",
                "",
                "• Maintain natural conversational tone",
                "• Ask questions when clarification is needed",
                "• Allow the trainee to drive the conversation",
                "• Do not produce long monologues",
                "",
                "---",
            ],
        ),
        _section(
            "## REALISTIC BEHAVIOR",
            realistic_behavior_lines,
        ),
        _section(
            "## CONVERSATION FLOW",
            [
                "",
                "The conversation may eventually conclude with outcomes such as:",
                "",
                *_format_list(end_conditions.get("possibleEndStates")),
                "",
                "However, do not rush the conversation to an ending.",
                "",
                "---",
            ],
        ),
        _section(
            "## LANGUAGE",
            [
                "",
                f"Use {_conversation_language(scenario, language)} for all responses.",
                "",
                "---",
            ],
        ),
        _section(
            "## START OF SIMULATION",
            [
                "",
                *_start_of_simulation_lines(conversation_start),
            ],
        ),
    ]
    return "\n\n".join(section for section in sections if section)


def resolve_opening_content(
    scenario: Any, language: str, who_talks_first: str | None
) -> tuple[str, bool]:
    if scenario is None:
        return _greeting_for_language(language), False

    simulation_config = _scenario_dict(scenario, "simulation_config", "simulationConfig")
    conversation_start = _as_dict(simulation_config.get("conversationStart"))
    normalized = _normalize_conversation_start_role(
        conversation_start.get("speakerRoleId")
    )
    if normalized == "trainee":
        initial_prompt = str(conversation_start.get("initialPromptToUser") or "").strip()
        if initial_prompt:
            return initial_prompt, False
        return _greeting_for_language(language), False
    return "", True


def resolve_bot_name(scenario: Any) -> str:
    if scenario is None:
        return FALLBACK_BOT_NAME
    simulation_config = _scenario_dict(scenario, "simulation_config", "simulationConfig")
    ai_persona = _as_dict(simulation_config.get("ai"))
    name = (ai_persona or {}).get("name") or ""
    return name or FALLBACK_BOT_NAME
