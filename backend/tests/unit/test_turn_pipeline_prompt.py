from types import SimpleNamespace

from app.services import turn_pipeline


def test_auto_prompt_used_when_prompt_missing():
    scenario = SimpleNamespace(
        title="Difficult feedback",
        description="A peer missed deadlines for two sprints.",
        prompt="",
        ai_persona={"name": "Alex", "role": "PM", "background": ""},
        trainee_persona={"name": "Jamie", "role": "Lead", "background": ""},
    )

    messages = turn_pipeline._build_initiation_messages(scenario)

    assert messages[1]["role"] == "user"
    assert "Start as Alex (PM)" in messages[1]["content"]
    assert "Context: Difficult feedback A peer missed deadlines" in messages[1]["content"]
    assert "invites a response" in messages[1]["content"]
