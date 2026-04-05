from types import SimpleNamespace

from app.api.routes.e2e_socket import (
    E2EConfig,
    _build_session_ready_payload,
    _build_start_session_payload,
)
from app.services.e2e_prompt_builder import resolve_bot_name, resolve_opening_content


def _make_config(**overrides) -> E2EConfig:
    defaults = {
        "ws_url": "wss://example.com/ws",
        "app_id": "test-app-id",
        "access_key": "test-access-key",
        "model": "test-model",
        "resource_id": "volc.speech.dialog",
        "app_key": "test-app-key",
        "speaker": "test-speaker",
    }
    defaults.update(overrides)
    return E2EConfig(**defaults)


def _make_scenario(**overrides) -> SimpleNamespace:
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
        "who_talks_first": "ai",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_build_payload_with_scenario_uses_dynamic_prompt():
    config = _make_config()
    scenario = _make_scenario()
    client_cfg: dict = {}

    payload = _build_start_session_payload(
        config, "sess-123", client_cfg, scenario=scenario, language="en"
    )

    dialog = payload["dialog"]
    assert "Salary Negotiation" in dialog["system_role"]
    assert "Jordan" in dialog["system_role"]
    assert "Practice asking for a raise." in dialog["system_role"]
    assert dialog["bot_name"] == "Jordan"
    assert dialog["dialog_id"] == "sess-123"


def test_build_payload_without_scenario_uses_fallback():
    config = _make_config()
    client_cfg: dict = {}

    payload = _build_start_session_payload(config, "sess-456", client_cfg)

    dialog = payload["dialog"]
    assert "AI communication coach" in dialog["system_role"]
    assert dialog["bot_name"] == "Real Talk Coach"


def test_resolve_opening_trainee_first():
    scenario = _make_scenario()
    content, needs_llm = resolve_opening_content(scenario, "en", "trainee")

    assert content == "Hey, what's up?"
    assert needs_llm is False


def test_resolve_opening_ai_first():
    scenario = _make_scenario()
    content, needs_llm = resolve_opening_content(scenario, "en", "ai")

    assert content == ""
    assert needs_llm is True


def test_resolve_opening_chinese_trainee_first():
    scenario = _make_scenario()
    content, needs_llm = resolve_opening_content(scenario, "zh", "trainee")

    assert content == "\u563f\uff0c\u6709\u4ec0\u4e48\u4e8b\u5417\uff1f"
    assert needs_llm is False


def test_bot_name_from_persona():
    scenario = _make_scenario()
    assert resolve_bot_name(scenario) == "Jordan"


def test_bot_name_fallback():
    assert resolve_bot_name(None) == "Real Talk Coach"


def test_build_payload_client_overrides_model_and_speaker():
    config = _make_config(model="default-model", speaker="default-speaker")
    client_cfg = {"model": "overridden-model", "speaker": "overridden-speaker"}

    payload = _build_start_session_payload(
        config, "sess-789", client_cfg, scenario=None
    )

    assert payload["dialog"]["extra"]["model"] == "overridden-model"
    assert payload["tts"]["speaker"] == "overridden-speaker"


def test_build_session_ready_payload_omits_debug_by_default():
    start_payload = {
        "dialog": {
            "system_role": "System prompt text",
        }
    }

    payload = _build_session_ready_payload(
        start_payload,
        "Opening text",
        send_debug_prompts=False,
    )

    assert payload == {"type": "session.ready"}


def test_build_session_ready_payload_includes_debug_when_requested():
    start_payload = {
        "dialog": {
            "system_role": "System prompt text",
        }
    }

    payload = _build_session_ready_payload(
        start_payload,
        "  Opening text  ",
        send_debug_prompts=True,
    )

    assert payload == {
        "type": "session.ready",
        "debug": {
            "systemPrompt": "System prompt text",
            "openingText": "Opening text",
        },
    }
