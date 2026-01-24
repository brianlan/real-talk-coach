from datetime import datetime, timedelta, timezone

import pytest

from app.models.session import enforce_drift
from app.services import objective_check


def test_enforce_drift_allows_within_tolerance():
    now = datetime.now(timezone.utc)
    enforce_drift(now, now + timedelta(seconds=1))


def test_enforce_drift_rejects_excessive_drift():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        enforce_drift(now, now + timedelta(seconds=5))


def test_objective_check_parses_tool_call():
    payload = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "arguments": '{"status":"succeeded","reason":"done"}'
                            }
                        }
                    ]
                }
            }
        ]
    }
    result = objective_check._parse_objective_response(payload)
    assert result.status == "succeeded"
    assert result.reason == "done"


def test_objective_check_handles_invalid_tool_json():
    payload = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"function": {"arguments": "{not-json}"}}
                    ]
                }
            }
        ]
    }
    result = objective_check._parse_objective_response(payload)
    assert result.status == "continue"


def test_objective_check_falls_back_to_message_content():
    payload = {"choices": [{"message": {"content": "keep going"}}]}
    result = objective_check._parse_objective_response(payload)
    assert result.status == "continue"
    assert result.reason == "keep going"
