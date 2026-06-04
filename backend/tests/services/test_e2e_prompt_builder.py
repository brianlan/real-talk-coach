"""Red-phase contract tests for e2e_prompt_builder against the new nested schema.

These tests encode the canonical nested scenario shape
(metadata/context/simulationConfig/evaluationConfig) and the canonical
system prompt template from the plan.  They are expected to FAIL until
the production prompt builder is refactored.
"""

import importlib
from types import SimpleNamespace

e2e_prompt_builder = importlib.import_module("app.services.e2e_prompt_builder")


# ---------------------------------------------------------------------------
# Canonical nested-scenario fixture (matches plan JSON)
# ---------------------------------------------------------------------------

def _make_nested_scenario(**overrides):
    """Return a SimpleNamespace that mirrors the canonical nested payload."""
    data = {
        "metadata": {
            "title": "Request a Salary Increase After Taking on Expanded Responsibilities",
            "slug": "salary-raise-expanded-responsibilities",
            "domain": "Workplace",
            "scenarioType": "Negotiation",
            "difficulty": "Medium",
            "conflictLevel": "Medium",
            "estimatedDurationMinutes": 8,
            "tags": ["salary negotiation", "career growth"],
        },
        "context": {
            "situation": (
                "An employee has taken on significant additional responsibilities "
                "after a teammate left the team."
            ),
            "background": (
                "The company is currently facing moderate budget pressure."
            ),
            "setting": "A scheduled one-on-one meeting between the employee and their manager.",
        },
        "simulationConfig": {
            "ai": {
                "name": "Jordan",
                "role": "Engineering Manager",
                "personality": ["professional", "pragmatic", "supportive but cautious"],
                "motivations": [
                    "retain high-performing employees",
                    "maintain fairness across the team",
                    "stay within departmental budget limits",
                ],
                "constraints": [
                    "raises above about 5-8% usually require director approval",
                    "the department budget is tight this quarter",
                ],
                "tendencies": [
                    "initially cautious when employees request raises",
                    "asks for justification and examples of impact",
                ],
                "knowledge": [
                    "the employee has taken on additional work after a teammate left",
                ],
                "emotionalState": "calm but slightly cautious",
            },
            "trainee": {
                "name": "Alex",
                "role": "Software Engineer",
                "personality": ["professional", "responsible", "thoughtful"],
                "motivations": [
                    "receive compensation that reflects expanded responsibilities",
                ],
                "constraints": [
                    "wants to avoid appearing confrontational",
                ],
                "tendencies": [
                    "prepared to explain additional responsibilities",
                ],
                "knowledge": [
                    "has researched market salaries for similar roles",
                ],
                "emotionalState": "motivated but slightly anxious",
            },
            "language": "English",
            "conversationStart": {
                "speakerRoleId": "employee",
                "initialPromptToUser": (
                    "You scheduled this meeting to discuss your compensation after "
                    "taking on additional responsibilities. Start the conversation."
                ),
            },
            "conversationRules": {
                "stayInCharacter": True,
                "allowNarration": False,
                "coachingAllowed": False,
                "tone": "natural professional conversation",
            },
            "conversationDynamics": {
                "typicalBehaviors": [
                    "ask the employee to explain expanded responsibilities",
                    "ask for examples of impact or results",
                    "mention budget limitations",
                ],
                "possibleResponses": [
                    "ask how the employee determined market salary benchmarks",
                    "mention internal fairness across the team",
                    "suggest revisiting compensation during the next performance cycle",
                ],
            },
            "decisionConstraints": {
                "approvalPolicy": {
                    "raiseCapPercent": 8,
                    "requiresDirectorApproval": True,
                },
                "fallbackPaths": [
                    "one-time bonus",
                    {"path": "promotion review", "timelineDays": 60},
                ],
            },
            "conversationEndConditions": {
                "possibleEndStates": [
                    "raise approved",
                    "timeline agreed for future salary review",
                    "discussion ends without agreement",
                ],
            },
        },
        "evaluationConfig": {
            "learningObjectives": [
                "make a clear compensation request",
                "support the request with evidence",
                "handle objections constructively",
                "work toward a concrete outcome or next step",
            ],
            "evaluationCriteria": [
                {
                    "id": "responsibility_articulation",
                    "description": (
                        "Trainee clearly explains expanded responsibilities "
                        "and their business impact"
                    ),
                },
                {
                    "id": "evidence_support",
                    "description": (
                        "Trainee references market benchmarks or other evidence "
                        "to support the compensation request"
                    ),
                },
                {
                    "id": "clear_request",
                    "description": (
                        "Trainee makes a clear and direct request for "
                        "compensation adjustment"
                    ),
                },
                {
                    "id": "handling_pushback",
                    "description": (
                        "Trainee responds constructively to concerns such as "
                        "budget limits or fairness"
                    ),
                },
                {
                    "id": "progress_toward_outcome",
                    "description": (
                        "Trainee works toward a concrete outcome such as a "
                        "raise, bonus, or timeline for review"
                    ),
                },
            ],
            "skillsAssessed": [
                "clear_request",
                "negotiation",
                "evidence_based_persuasion",
                "handling_objections",
                "professional_workplace_communication",
            ],
            "scoring": {
                "scale": "1-5",
                "criteriaWeighting": {
                    "responsibility_articulation": 0.2,
                    "evidence_support": 0.2,
                    "clear_request": 0.2,
                    "handling_pushback": 0.2,
                    "progress_toward_outcome": 0.2,
                },
            },
            "evaluationInstructionsForLLM": (
                "Evaluate the trainee's performance using the conversation transcript. "
                "Focus on clarity of the request, supporting evidence, ability to handle "
                "objections, and progress toward a concrete outcome."
            ),
        },
    }
    data.update(overrides)
    return SimpleNamespace(**data)


# ---------------------------------------------------------------------------
# Tests for build_e2e_system_prompt
# ---------------------------------------------------------------------------

def test_build_e2e_system_prompt_returns_fallback_when_scenario_missing():
    result = e2e_prompt_builder.build_e2e_system_prompt(None, "en")

    assert (
        result
        == "You are an AI communication coach helping the user practice difficult conversations."
    )


def test_build_e2e_system_prompt_includes_role_section():
    """The prompt must include the 'ROLE YOU ARE PLAYING' section with AI persona fields."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert result.startswith("You are running a conversation practice simulation.")
    assert "Your job is to roleplay a character in a realistic conversation" in result
    assert "Follow the instructions carefully." in result
    assert "## ROLE YOU ARE PLAYING" in result
    assert "Jordan" in result
    assert "Engineering Manager" in result


def test_build_e2e_system_prompt_includes_ai_persona_fields():
    """AI personality, motivations, constraints, tendencies, emotional state must appear."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    # Personality
    assert "professional" in result
    assert "pragmatic" in result
    # Motivations
    assert "retain high-performing employees" in result
    # Constraints
    assert "raises above about 5-8% usually require director approval" in result
    # Tendencies
    assert "initially cautious when employees request raises" in result
    # Emotional state
    assert "calm but slightly cautious" in result


def test_build_e2e_system_prompt_includes_scenario_context():
    """The SCENARIO CONTEXT section must include situation, background, setting."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "## SCENARIO CONTEXT" in result
    assert scenario.context["situation"] in result
    assert scenario.context["background"] in result
    assert scenario.context["setting"] in result


def test_build_e2e_system_prompt_includes_trainee_context():
    """The TRAINEE ROLE section must include trainee name, role, knowledge, emotional state."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "## TRAINEE ROLE (FOR CONTEXT ONLY)" in result
    assert "Alex" in result
    assert "Software Engineer" in result
    assert "has researched market salaries for similar roles" in result
    assert "motivated but slightly anxious" in result


def test_build_e2e_system_prompt_includes_roleplay_rules():
    """ROLEPLAY RULES section with in-character / no-narration / no-coaching."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "## ROLEPLAY RULES" in result
    assert "Stay fully in character." in result
    assert "Never narrate actions, stage directions, or internal thoughts." in result
    assert "Do NOT give advice, coaching, or feedback." in result


def test_build_e2e_system_prompt_includes_conversation_style():
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "## CONVERSATION STYLE" in result
    assert "• Maintain natural conversational tone" in result
    assert "• Ask questions when clarification is needed" in result
    assert "• Allow the trainee to drive the conversation" in result
    assert "• Do not produce long monologues" in result


def test_build_e2e_system_prompt_includes_conversation_dynamics():
    """REALISTIC BEHAVIOR section must embed typical behaviors and possible responses."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "## REALISTIC BEHAVIOR" in result
    dynamics = scenario.simulationConfig["conversationDynamics"]
    for behavior in dynamics["typicalBehaviors"]:
        assert behavior in result
    for response in dynamics["possibleResponses"]:
        assert response in result


def test_build_e2e_system_prompt_includes_generic_decision_constraints_json():
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "Keep the following constraints in mind:" in result
    assert "## DECISION CONSTRAINTS" not in result
    assert "• approvalPolicy:" in result
    assert "• raiseCapPercent: 8" in result
    assert "• requiresDirectorApproval: true" in result
    assert "• fallbackPaths:" in result
    assert "• one-time bonus" in result
    assert "• path: promotion review" in result
    assert "• timelineDays: 60" in result


def test_build_e2e_system_prompt_omits_decision_constraints_when_empty():
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
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "Keep the following constraints in mind:" not in result
    assert "approvalPolicy" not in result
    assert "fallbackPaths" not in result


def test_build_e2e_system_prompt_includes_conversation_end_states():
    """CONVERSATION FLOW section must list possible end states."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "## CONVERSATION FLOW" in result
    assert "The conversation may eventually conclude with outcomes such as:" in result
    assert "However, do not rush the conversation to an ending." in result
    for state in scenario.simulationConfig["conversationEndConditions"]["possibleEndStates"]:
        assert state in result


def test_build_e2e_system_prompt_does_not_include_learning_objectives_in_flow():
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "make a clear compensation request" not in result


def test_build_e2e_system_prompt_includes_language_directive():
    """Language directive must use simulationConfig.language or the language parameter."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "## LANGUAGE" in result
    assert "Use English for all responses." in result


def test_build_e2e_system_prompt_uses_chinese_for_zh():
    """When language=zh, the language directive must say Chinese."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "zh")

    assert "Use Chinese for all responses." in result


def test_build_e2e_system_prompt_includes_start_of_simulation():
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    assert "## START OF SIMULATION" in result
    assert "The trainee will begin the conversation." in result
    assert "Wait for the trainee's first message and respond naturally as your character." in result


def test_build_e2e_system_prompt_does_not_use_legacy_fields():
    """The prompt must NOT contain legacy flat-field references like
    'Scenario title:' or 'Scenario description:' or 'Additional instructions:'."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.build_e2e_system_prompt(scenario, "en")

    # These are the OLD prompt format markers that must disappear
    assert "Scenario title:" not in result
    assert "Scenario description:" not in result
    assert "Additional instructions:" not in result
    assert "Your persona:" not in result
    assert "Trainee persona:" not in result


# ---------------------------------------------------------------------------
# Tests for resolve_opening_content
# ---------------------------------------------------------------------------

def test_resolve_opening_content_trainee_start_returns_initial_prompt():
    """When conversationStart.speakerRoleId indicates trainee starts,
    the function must return initialPromptToUser and needs_llm=False."""
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.resolve_opening_content(
        scenario, "en",
        who_talks_first="trainee",
    )

    prompt_text, needs_llm = result
    assert prompt_text == (
        "You scheduled this meeting to discuss your compensation after "
        "taking on additional responsibilities. Start the conversation."
    )
    assert needs_llm is False


def test_resolve_opening_content_ai_start_returns_empty_and_needs_llm():
    """When speakerRoleId indicates AI starts, returns ('', True)."""
    overrides = {
        "simulationConfig": {
            **_make_nested_scenario().simulationConfig,
            "conversationStart": {
                "speakerRoleId": "ai",
                "initialPromptToUser": "",
            },
        },
    }
    scenario = _make_nested_scenario(**overrides)
    result = e2e_prompt_builder.resolve_opening_content(
        scenario, "en",
        who_talks_first="ai",
    )

    prompt_text, needs_llm = result
    assert prompt_text == ""
    assert needs_llm is True


def test_resolve_opening_content_defaults_invalid_to_ai():
    scenario = _make_nested_scenario()
    result = e2e_prompt_builder.resolve_opening_content(
        scenario, "en",
        who_talks_first="host",
    )

    prompt_text, needs_llm = result
    assert prompt_text == (
        "You scheduled this meeting to discuss your compensation after "
        "taking on additional responsibilities. Start the conversation."
    )
    assert needs_llm is False


def test_resolve_opening_content_defaults_to_ai_when_nested_start_missing():
    scenario = _make_nested_scenario(
        simulationConfig={
            **_make_nested_scenario().simulationConfig,
            "conversationStart": {},
        }
    )

    prompt_text, needs_llm = e2e_prompt_builder.resolve_opening_content(
        scenario, "en", who_talks_first="ai"
    )

    assert prompt_text == ""
    assert needs_llm is True


def test_resolve_opening_content_scenario_missing_returns_greeting():
    """When scenario is None, return a greeting and needs_llm=False."""
    result = e2e_prompt_builder.resolve_opening_content(None, "en", "ai")
    prompt_text, needs_llm = result
    assert prompt_text  # non-empty greeting
    assert needs_llm is False


# ---------------------------------------------------------------------------
# Tests for resolve_bot_name
# ---------------------------------------------------------------------------

def test_resolve_bot_name_returns_ai_persona_name():
    """Bot name must come from simulationConfig.ai.name."""
    scenario = _make_nested_scenario()
    assert e2e_prompt_builder.resolve_bot_name(scenario) == "Jordan"


def test_resolve_bot_name_falls_back_to_default():
    """When ai persona has no name, fall back to default."""
    overrides = {
        "simulationConfig": {
            **_make_nested_scenario().simulationConfig,
            "ai": {
                **_make_nested_scenario().simulationConfig["ai"],
                "name": "",
            },
        },
    }
    scenario = _make_nested_scenario(**overrides)
    assert e2e_prompt_builder.resolve_bot_name(scenario) == "Real Talk Coach"
    assert e2e_prompt_builder.resolve_bot_name(None) == "Real Talk Coach"
