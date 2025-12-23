import pytest

from app.services import turn_pipeline


@pytest.mark.asyncio
async def test_turn_pipeline_emits_metrics_on_audio_error(monkeypatch):
    events = []
    metrics = []

    async def fake_update_turn(turn_id, payload):
        return None

    async def fake_update_session(session_id, payload):
        return None

    class FakeRepo:
        update_turn = staticmethod(fake_update_turn)
        update_session = staticmethod(fake_update_session)

    async def fake_broadcast(self, session_id, payload):
        return None

    def fake_emit_event(name, **kwargs):
        events.append((name, kwargs))

    def fake_emit_metric(name, value, **kwargs):
        metrics.append((name, value, kwargs))

    monkeypatch.setattr(turn_pipeline, "emit_event", fake_emit_event)
    monkeypatch.setattr(turn_pipeline, "emit_metric", fake_emit_metric)
    monkeypatch.setattr(turn_pipeline, "hub", type("Hub", (), {"broadcast": fake_broadcast})())

    await turn_pipeline._handle_audio_error(FakeRepo(), "session-1", "turn-1", "bad audio")

    assert any(event[0] == "turn.audio_error" for event in events)
    assert any(metric[0] == "turn.audio_error" for metric in metrics)
