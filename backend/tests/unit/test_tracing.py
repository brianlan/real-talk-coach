import json

from app.telemetry.tracing import build_sc_attributes, emit_event, emit_metric


def _last_payload(caplog):
    assert caplog.records
    return json.loads(caplog.records[-1].message)


def test_emit_event_includes_session_turn_and_sc_attributes(caplog):
    caplog.set_level("INFO")
    attributes = build_sc_attributes("SC-001", {"status": "completed"})

    emit_event(
        "session.completed",
        session_id="session-1",
        turn_id="turn-2",
        attributes=attributes,
    )

    payload = _last_payload(caplog)
    assert payload["type"] == "event"
    assert payload["sessionId"] == "session-1"
    assert payload["turnId"] == "turn-2"
    assert payload["attributes"]["sc_id"] == "SC-001"


def test_emit_metric_includes_value_and_ids(caplog):
    caplog.set_level("INFO")
    attributes = build_sc_attributes("SC-002")

    emit_metric(
        "termination.latency",
        1.5,
        session_id="session-1",
        turn_id="turn-9",
        attributes=attributes,
    )

    payload = _last_payload(caplog)
    assert payload["type"] == "metric"
    assert payload["value"] == 1.5
    assert payload["sessionId"] == "session-1"
    assert payload["turnId"] == "turn-9"
    assert payload["attributes"]["sc_id"] == "SC-002"
