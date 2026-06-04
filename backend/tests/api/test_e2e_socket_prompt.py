"""Red-phase contract tests for e2e_socket prompt/opening helpers.

These tests encode the canonical nested scenario shape and verify the
new prompt/opening contracts.  They are expected to FAIL until the
production code is refactored.
"""

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


def _make_nested_scenario(**overrides):
    data = {
        "metadata": {
            "title": "Request a Salary Increase After Taking on Expanded Responsibilities",
            "slug": "salary-raise-expanded-responsibilities",
            "domain": "Workplace",
            "scenarioType": "Negotiation",
            "difficulty": "Medium",
            "conflictLevel": "Medium",
            "estimatedDurationMinutes": 8,
            "tags": ["salary negotiation"],
        },
        "context": {
            "situation": "An employee has taken on significant additional responsibilities.",
            "background": "The company is currently facing moderate budget pressure.",
            "setting": "A scheduled one-on-one meeting.",
        },
        "simulationConfig": {
            "ai": {
                "name": "Jordan",
                "role": "Engineering Manager",
                "personality": ["professional", "pragmatic"],
                "motivations": ["retain high-performing employees"],
                "constraints": ["raises above 5-8% require director approval"],
                "tendencies": ["initially cautious"],
                "knowledge": ["the employee has taken on additional work"],
                "emotionalState": "calm but slightly cautious",
            },
            "trainee": {
                "name": "Alex",
                "role": "Software Engineer",
                "personality": ["professional"],
                "motivations": ["receive compensation that reflects expanded responsibilities"],
                "constraints": ["wants to avoid appearing confrontational"],
                "tendencies": ["prepared to explain additional responsibilities"],
                "knowledge": ["has researched market salaries for similar roles"],
                "emotionalState": "motivated but slightly anxious",
            },
            "language": "English",
            "conversationStart": {
                "speakerRoleId": "employee",
                "initialPromptToUser": (
                    "You scheduled this meeting to discuss your compensation. "
                    "Start the conversation."
                ),
            },
            "conversationRules": {
                "stayInCharacter": True,
                "allowNarration": False,
                "coachingAllowed": False,
                "tone": "natural professional conversation",
            },
            "conversationDynamics": {
                "typicalBehaviors": ["ask the employee to explain expanded responsibilities"],
                "possibleResponses": ["mention internal fairness across the team"],
            },
            "decisionConstraints": {
                "approvalPolicy": {
                    "raiseCapPercent": 8,
                    "requiresDirectorApproval": True,
                },
                "fallbackPaths": ["one-time bonus"],
            },
            "conversationEndConditions": {
                "possibleEndStates": ["raise approved", "discussion ends without agreement"],
            },
        },
        "evaluationConfig": {
            "learningObjectives": ["make a clear compensation request"],
            "evaluationCriteria": [
                {"id": "clear_request", "description": "Trainee makes a clear compensation request"},
            ],
            "skillsAssessed": ["clear_request", "negotiation"],
            "scoring": {"scale": "1-5", "criteriaWeighting": {"clear_request": 1.0}},
            "evaluationInstructionsForLLM": "Evaluate the trainee.",
        },
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_build_payload_uses_nested_prompt_template():
    """The dialog system_role must contain the new nested prompt template sections."""
    config = _make_config()
    scenario = _make_nested_scenario()
    client_cfg: dict = {}

    payload = _build_start_session_payload(
        config, "sess-123", client_cfg, scenario=scenario, language="en"
    )

    dialog = payload["dialog"]
    system_role = dialog["system_role"]

    # New template section markers
    assert system_role.startswith("You are running a conversation practice simulation.")
    assert "## ROLE YOU ARE PLAYING" in system_role
    assert "## TRAINEE ROLE (FOR CONTEXT ONLY)" in system_role
    assert "## CONVERSATION STYLE" in system_role
    assert "## START OF SIMULATION" in system_role
    assert "Keep the following constraints in mind:" in system_role
    assert "• approvalPolicy:" in system_role
    assert "• raiseCapPercent: 8" in system_role
    assert "• requiresDirectorApproval: true" in system_role
    assert "• fallbackPaths:" in system_role
    assert "• one-time bonus" in system_role
    assert "Jordan" in system_role
    assert "Engineering Manager" in system_role

    # Legacy markers must NOT appear
    assert "Scenario title:" not in system_role
    assert "Scenario description:" not in system_role
    assert "## DECISION CONSTRAINTS" not in system_role


def test_build_payload_omits_constraints_block_when_decision_constraints_empty():
    config = _make_config()
    client_cfg: dict = {}
    scenario = _make_nested_scenario(
        simulationConfig={
            **_make_nested_scenario().simulationConfig,
            "decisionConstraints": {
                "approvalPolicy": {},
                "fallbackPaths": [],
                "notes": "   ",
            },
        }
    )

    payload = _build_start_session_payload(
        config, "sess-124", client_cfg, scenario=scenario, language="en"
    )

    system_role = payload["dialog"]["system_role"]
    assert "Keep the following constraints in mind:" not in system_role
    assert "approvalPolicy" not in system_role
    assert "fallbackPaths" not in system_role


def test_build_payload_bot_name_from_nested_ai_persona():
    """bot_name must come from simulationConfig.ai.name."""
    config = _make_config()
    scenario = _make_nested_scenario()
    client_cfg: dict = {}

    payload = _build_start_session_payload(
        config, "sess-123", client_cfg, scenario=scenario, language="en"
    )

    assert payload["dialog"]["bot_name"] == "Jordan"


def test_build_payload_without_scenario_uses_fallback():
    config = _make_config()
    client_cfg: dict = {}

    payload = _build_start_session_payload(config, "sess-456", client_cfg)

    dialog = payload["dialog"]
    assert "AI communication coach" in dialog["system_role"]
    assert dialog["bot_name"] == "Real Talk Coach"


def test_resolve_opening_trainee_first_uses_initial_prompt():
    """When speakerRoleId is 'employee', the opening must use initialPromptToUser."""
    scenario = _make_nested_scenario()
    content, needs_llm = resolve_opening_content(scenario, "en", "trainee")

    assert content == (
        "You scheduled this meeting to discuss your compensation. "
        "Start the conversation."
    )
    assert needs_llm is False


def test_resolve_opening_ai_first():
    scenario = _make_nested_scenario()
    content, needs_llm = resolve_opening_content(scenario, "en", "ai")

    assert content == (
        "You scheduled this meeting to discuss your compensation. "
        "Start the conversation."
    )
    assert needs_llm is False


def test_resolve_opening_ai_first_when_nested_start_is_ai():
    scenario = _make_nested_scenario(
        simulationConfig={
            **_make_nested_scenario().simulationConfig,
            "conversationStart": {
                "speakerRoleId": "ai",
                "initialPromptToUser": "",
            },
        }
    )

    content, needs_llm = resolve_opening_content(scenario, "en", "trainee")

    assert content == ""
    assert needs_llm is True


def test_resolve_opening_defaults_to_ai_when_nested_start_missing():
    scenario = _make_nested_scenario(
        simulationConfig={
            **_make_nested_scenario().simulationConfig,
            "conversationStart": {},
        }
    )

    content, needs_llm = resolve_opening_content(scenario, "en", "trainee")

    assert content == ""
    assert needs_llm is True


def test_bot_name_from_nested_persona():
    scenario = _make_nested_scenario()
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
