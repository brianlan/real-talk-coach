import importlib
from types import SimpleNamespace

e2e_prompt_builder = importlib.import_module("app.services.e2e_prompt_builder")


def make_scenario(**overrides):
    data = {
        "title": "Salary Negotiation",
        "description": "Practice asking for a raise.",
        "objective": "Get agreement to revisit compensation.",
        "end_criteria": ["Manager acknowledges impact", "Next step is agreed"],
        "prompt": "Be firm but fair.",
        "ai_persona": {
            "name": "Jordan",
            "role": "Manager",
            "background": "Busy but open to discussion",
        },
        "trainee_persona": {
            "name": "Taylor",
            "role": "Engineer",
            "background": "Senior individual contributor",
        },
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_build_e2e_system_prompt_returns_fallback_when_scenario_missing():
    result = e2e_prompt_builder.build_e2e_system_prompt(None, "en")

    assert (
        result
        == "You are an AI communication coach helping the user practice difficult conversations."
    )


def test_build_e2e_system_prompt_includes_all_scenario_fields():
    result = e2e_prompt_builder.build_e2e_system_prompt(make_scenario(), "en")

    assert "You are the AI roleplayer for a practice conversation." in result
    assert "Your persona: Jordan (Manager). Background: Busy but open to discussion" in result
    assert "Trainee persona: Taylor (Engineer). Background: Senior individual contributor" in result
    assert "Scenario title: Salary Negotiation" in result
    assert "Scenario description: Practice asking for a raise." in result
    assert "Objective: Get agreement to revisit compensation." in result
    assert "End criteria:" in result
    assert "- Manager acknowledges impact" in result
    assert "- Next step is agreed" in result
    assert "Additional instructions: Be firm but fair." in result
    assert "Use English for all responses." in result
    assert "Stay in character and respond naturally to the trainee." in result


def test_build_e2e_system_prompt_omits_additional_instructions_when_prompt_blank():
    result = e2e_prompt_builder.build_e2e_system_prompt(make_scenario(prompt=""), "en")

    assert "Additional instructions:" not in result


def test_build_e2e_system_prompt_uses_simplified_chinese_label():
    result = e2e_prompt_builder.build_e2e_system_prompt(make_scenario(), "zh")

    assert "Use Simplified Chinese for all responses." in result


def test_build_e2e_system_prompt_handles_missing_personas_and_end_criteria():
    result = e2e_prompt_builder.build_e2e_system_prompt(
        make_scenario(ai_persona=None, trainee_persona=None, end_criteria=[]), "en"
    )

    assert "Your persona: (not provided)" in result
    assert "Trainee persona: (not provided)" in result
    assert "End criteria:\n- Not provided" in result


def test_resolve_opening_content_returns_llm_generation_for_ai_first():
    result = e2e_prompt_builder.resolve_opening_content(make_scenario(), "en", "ai")

    assert result == ("", True)


def test_resolve_opening_content_defaults_invalid_who_talks_first_to_ai():
    result = e2e_prompt_builder.resolve_opening_content(make_scenario(), "en", "host")

    assert result == ("", True)


def test_resolve_opening_content_returns_english_greeting_for_trainee_first():
    result = e2e_prompt_builder.resolve_opening_content(make_scenario(), "en", "trainee")

    assert result == ("Hey, what's up?", False)


def test_resolve_opening_content_returns_chinese_greeting_for_trainee_first():
    result = e2e_prompt_builder.resolve_opening_content(make_scenario(), "zh", "trainee")

    assert result == ("嘿，有什么事吗？", False)


def test_resolve_opening_content_returns_casual_greeting_when_scenario_missing():
    assert e2e_prompt_builder.resolve_opening_content(None, "en", "ai") == (
        "Hey, what's up?",
        False,
    )
    assert e2e_prompt_builder.resolve_opening_content(None, "zh", "ai") == (
        "嘿，有什么事吗？",
        False,
    )


def test_resolve_bot_name_returns_ai_persona_name():
    assert e2e_prompt_builder.resolve_bot_name(make_scenario()) == "Jordan"


def test_resolve_bot_name_falls_back_to_default_name():
    scenario = make_scenario(ai_persona={"name": "", "role": "Manager", "background": ""})

    assert e2e_prompt_builder.resolve_bot_name(scenario) == "Real Talk Coach"
    assert e2e_prompt_builder.resolve_bot_name(None) == "Real Talk Coach"
