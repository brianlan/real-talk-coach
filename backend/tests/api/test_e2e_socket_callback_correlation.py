import asyncio
import gzip
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.api.routes import history as history_routes
from app.api.routes.e2e_socket import (
    E2EConfig,
    _finalize_realtime_session,
    _persist_callback_session_correlation,
    _persist_opening_prompt,
)
from app.main import app
from app.repositories.evaluation_repository import EvaluationRecord
from app.repositories.session_repository import PracticeSessionRecord
from app.services import session_service


@pytest.fixture(autouse=True)
def _reset_session_service_state(monkeypatch):
    session_service._FINALIZE_LOCKS.clear()
    session_service._PENDING_EVALUATION_TASKS.clear()
    session_service._EVALUATION_ENQUEUED.clear()
    monkeypatch.setattr(session_service, "_REALTIME_EVALUATION_GRACE_SECONDS", 0.0)


@pytest.mark.asyncio
async def test_persist_callback_session_correlation_stores_runtime_session_as_lookup_key():
    repo = AsyncMock()

    await _persist_callback_session_correlation(
        repo,
        "507f1f77bcf86cd799439011",
        "507f1f77bcf86cd799439011",
    )

    repo.update_session.assert_awaited_once_with(
        "507f1f77bcf86cd799439011",
        {
            "mode": "realtime",
            "rtcRoomId": "507f1f77bcf86cd799439011",
            "realtimeState": "connecting",
        },
    )


@pytest.mark.asyncio
async def test_persist_callback_session_correlation_skips_empty_identifiers():
    repo = AsyncMock()

    await _persist_callback_session_correlation(repo, "", "")

    repo.update_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_persist_opening_prompt_skips_blank_content():
    repo = AsyncMock()

    await _persist_opening_prompt(repo, "session-1", "   ")

    repo.update_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_persist_opening_prompt_stores_trimmed_text():
    repo = AsyncMock()

    await _persist_opening_prompt(repo, "session-1", "  Hello there.  ")

    repo.update_session.assert_awaited_once_with(
        "session-1",
        {"openingPrompt": "Hello there."},
    )


@pytest.mark.asyncio
async def test_finalize_realtime_session_marks_terminal_state_once(monkeypatch):
    repo = AsyncMock()
    session = SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        status="active",
        termination_reason=None,
        ended_at=None,
        evaluation_id=None,
        mode="realtime",
    )
    ended_session = SimpleNamespace(
        id=session.id,
        status="ended",
        termination_reason="manual",
        ended_at="2026-01-01T00:00:00+00:00",
        evaluation_id=None,
        mode="realtime",
    )

    repo.get_session = AsyncMock(side_effect=[session, ended_session])
    repo.update_session = AsyncMock(return_value=ended_session)
    repo.list_turns = AsyncMock(return_value=[SimpleNamespace(id="turn-1")])

    enqueue_calls: list[str] = []

    def fake_enqueue(session_id: str) -> None:
        enqueue_calls.append(session_id)

    monkeypatch.setattr("app.services.session_service.enqueue", fake_enqueue)

    await _finalize_realtime_session(repo, session.id, termination_reason=None)
    await _finalize_realtime_session(repo, session.id, termination_reason="upstream_finish")

    update_payload = repo.update_session.await_args_list[0].args[1]
    assert update_payload["status"] == "ended"
    assert update_payload["realtimeState"] == "ended"
    assert "terminationReason" not in update_payload
    assert enqueue_calls == [session.id]


@pytest.mark.asyncio
async def test_finalize_realtime_session_preserves_existing_reason(monkeypatch):
    repo = AsyncMock()
    ended_session = SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        status="ended",
        termination_reason="manual",
        ended_at="2026-01-01T00:00:00+00:00",
        evaluation_id=None,
        mode="realtime",
    )

    repo.get_session = AsyncMock(return_value=ended_session)
    repo.update_session = AsyncMock(return_value=ended_session)
    repo.list_turns = AsyncMock(return_value=[SimpleNamespace(id="turn-1")])

    enqueue_calls: list[str] = []

    def fake_enqueue(session_id: str) -> None:
        enqueue_calls.append(session_id)

    monkeypatch.setattr("app.services.session_service.enqueue", fake_enqueue)

    await _finalize_realtime_session(repo, ended_session.id, termination_reason="upstream_finish")
    await asyncio.sleep(0)

    update_payload = repo.update_session.await_args.args[1]
    assert update_payload["terminationReason"] == "manual"
    assert update_payload["realtimeState"] == "ended"
    assert enqueue_calls == [ended_session.id]


def _build_server_ack(event: int, payload: dict | None = None, session_id: str = "runtime-session") -> bytes:
    payload_obj = payload or {}
    payload_bytes = gzip.compress(json.dumps(payload_obj).encode("utf-8"))
    sid = session_id.encode("utf-8")
    packet = bytearray()
    packet.append(0x11)
    packet.append(0xB4)
    packet.append(0x11)
    packet.append(0x00)
    packet.extend(int(event).to_bytes(4, "big"))
    packet.extend(len(sid).to_bytes(4, "big"))
    packet.extend(sid)
    packet.extend(len(payload_bytes).to_bytes(4, "big"))
    packet.extend(payload_bytes)
    return bytes(packet)


@pytest.mark.asyncio
async def test_e2e_websocket_disconnect_finalizes_session_once(monkeypatch):
    from app.api.routes import e2e_socket as e2e_routes
    from app.services import session_service

    session_service._FINALIZE_LOCKS.clear()
    session_service._PENDING_EVALUATION_TASKS.clear()
    session_service._EVALUATION_ENQUEUED.clear()

    session = PracticeSessionRecord(
        id="507f1f77bcf86cd799439011",
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        user_id=None,
        language="en",
        opening_prompt=None,
        status="active",
        client_session_started_at="2026-01-01T00:00:00+00:00",
        started_at="2026-01-01T00:00:00+00:00",
        ended_at=None,
        total_duration_seconds=None,
        idle_limit_seconds=None,
        duration_limit_seconds=None,
        ws_channel="/ws/sessions/507f1f77bcf86cd799439011",
        objective_status="unknown",
        objective_reason=None,
        termination_reason=None,
        evaluation_id=None,
        mode="realtime",
        rtc_room_id=None,
        rtc_task_id=None,
        realtime_state=None,
    )
    updates: list[dict] = []

    def apply_update(record: PracticeSessionRecord, payload: dict) -> PracticeSessionRecord:
        data = record.__dict__.copy()
        mapping = {
            "status": "status",
            "terminationReason": "termination_reason",
            "endedAt": "ended_at",
            "mode": "mode",
            "rtcRoomId": "rtc_room_id",
            "rtcTaskId": "rtc_task_id",
            "realtimeState": "realtime_state",
        }
        for key, value in payload.items():
            field = mapping.get(key)
            if field:
                data[field] = value
        return PracticeSessionRecord(**data)

    async def fake_get_session(self, session_id: str):
        return session if session_id == session.id else None

    async def fake_update_session(self, session_id: str, payload: dict):
        nonlocal session
        if session_id != session.id:
            return None
        updates.append(dict(payload))
        session = apply_update(session, payload)
        return session

    async def fake_list_turns(self, session_id: str):
        if session_id != session.id:
            return []
        return [SimpleNamespace(id="turn-1")]

    async def fake_get_scenario(self, scenario_id: str):
        return SimpleNamespace(
            id=scenario_id,
            metadata={"title": "Test Scenario"},
            context={"situation": "Test"},
            simulation_config={
                "ai": {"name": "Coach", "role": "Coach"},
                "trainee": {"name": "Trainee", "role": "Trainee"},
                "conversationStart": {"speakerRoleId": "trainee", "initialPromptToUser": "Begin."},
            },
            evaluation_config={},
        )

    class FakeUpstream:
        def __init__(self):
            self.sent: list[bytes] = []
            self._recv_packets = [
                _build_server_ack(1, {}),
                _build_server_ack(100, {}),
            ]

        async def send(self, packet: bytes):
            self.sent.append(packet)

        async def recv(self):
            return self._recv_packets.pop(0)

        def __aiter__(self):
            return self

        async def __anext__(self):
            await asyncio.Future()

    class FakeConnect:
        def __init__(self):
            self.upstream = FakeUpstream()

        async def __aenter__(self):
            return self.upstream

        async def __aexit__(self, exc_type, exc, tb):
            return False

    enqueue_calls: list[str] = []

    def fake_enqueue(session_id: str) -> None:
        enqueue_calls.append(session_id)

    monkeypatch.setattr(e2e_routes, "_load_e2e_config", lambda: E2EConfig(
        ws_url="wss://example.test/ws",
        app_id="app-id",
        access_key="token",
        model=None,
        resource_id="volc.speech.dialog",
        app_key="app-key",
        speaker=None,
    ))
    monkeypatch.setattr(e2e_routes, "ws_connect", lambda *args, **kwargs: FakeConnect())
    monkeypatch.setattr("app.repositories.session_repository.SessionRepository.get_session", fake_get_session)
    monkeypatch.setattr("app.repositories.session_repository.SessionRepository.update_session", fake_update_session)
    monkeypatch.setattr("app.repositories.session_repository.SessionRepository.list_turns", fake_list_turns)
    monkeypatch.setattr("app.repositories.scenario_repository.ScenarioRepository.get", fake_get_scenario)
    monkeypatch.setattr("app.services.session_service.enqueue", fake_enqueue)

    websocket = AsyncMock()
    websocket.app = SimpleNamespace(state=SimpleNamespace(mongodb=MagicMock()))
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock()
    websocket.receive = AsyncMock(
        side_effect=[
            {"type": "websocket.receive", "text": json.dumps({"type": "session.update", "session": {"send_opening": False}})},
            {"type": "websocket.disconnect"},
        ]
    )

    await e2e_routes.e2e_voice_socket(websocket, session.id)

    assert session.status == "ended"
    assert session.realtime_state == "ended"
    assert enqueue_calls == [session.id]
    terminal_updates = [payload for payload in updates if payload.get("status") == "ended"]
    assert len(terminal_updates) == 1


@pytest.mark.asyncio
async def test_e2e_websocket_upstream_finish_finalizes_session_once(monkeypatch):
    from app.api.routes import e2e_socket as e2e_routes
    from app.services import session_service

    session_service._FINALIZE_LOCKS.clear()
    session_service._PENDING_EVALUATION_TASKS.clear()
    session_service._EVALUATION_ENQUEUED.clear()

    session = PracticeSessionRecord(
        id="507f1f77bcf86cd799439099",
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        user_id=None,
        language="en",
        opening_prompt=None,
        status="active",
        client_session_started_at="2026-01-01T00:00:00+00:00",
        started_at="2026-01-01T00:00:00+00:00",
        ended_at=None,
        total_duration_seconds=None,
        idle_limit_seconds=None,
        duration_limit_seconds=None,
        ws_channel="/ws/sessions/507f1f77bcf86cd799439099",
        objective_status="unknown",
        objective_reason=None,
        termination_reason=None,
        evaluation_id=None,
        mode="realtime",
        rtc_room_id=None,
        rtc_task_id=None,
        realtime_state=None,
    )
    updates: list[dict] = []

    def apply_update(record: PracticeSessionRecord, payload: dict) -> PracticeSessionRecord:
        data = record.__dict__.copy()
        mapping = {
            "status": "status",
            "terminationReason": "termination_reason",
            "endedAt": "ended_at",
            "mode": "mode",
            "rtcRoomId": "rtc_room_id",
            "rtcTaskId": "rtc_task_id",
            "realtimeState": "realtime_state",
        }
        for key, value in payload.items():
            field = mapping.get(key)
            if field:
                data[field] = value
        return PracticeSessionRecord(**data)

    async def fake_get_session(self, session_id: str):
        return session if session_id == session.id else None

    async def fake_update_session(self, session_id: str, payload: dict):
        nonlocal session
        if session_id != session.id:
            return None
        updates.append(dict(payload))
        session = apply_update(session, payload)
        return session

    async def fake_list_turns(self, session_id: str):
        if session_id != session.id:
            return []
        return [SimpleNamespace(id="turn-1")]

    async def fake_get_scenario(self, scenario_id: str):
        return SimpleNamespace(
            id=scenario_id,
            metadata={"title": "Test Scenario"},
            context={"situation": "Test"},
            simulation_config={
                "ai": {"name": "Coach", "role": "Coach"},
                "trainee": {"name": "Trainee", "role": "Trainee"},
                "conversationStart": {"speakerRoleId": "trainee", "initialPromptToUser": "Begin."},
            },
            evaluation_config={},
        )

    class FakeUpstream:
        def __init__(self):
            self.sent: list[bytes] = []
            self._recv_packets = [
                _build_server_ack(1, {}),
                _build_server_ack(100, {}),
            ]

        async def send(self, packet: bytes):
            self.sent.append(packet)

        async def recv(self):
            return self._recv_packets.pop(0)

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class FakeConnect:
        def __init__(self):
            self.upstream = FakeUpstream()

        async def __aenter__(self):
            return self.upstream

        async def __aexit__(self, exc_type, exc, tb):
            return False

    enqueue_calls: list[str] = []

    def fake_enqueue(session_id: str) -> None:
        enqueue_calls.append(session_id)

    monkeypatch.setattr(e2e_routes, "_load_e2e_config", lambda: E2EConfig(
        ws_url="wss://example.test/ws",
        app_id="app-id",
        access_key="token",
        model=None,
        resource_id="volc.speech.dialog",
        app_key="app-key",
        speaker=None,
    ))
    monkeypatch.setattr(e2e_routes, "ws_connect", lambda *args, **kwargs: FakeConnect())
    monkeypatch.setattr("app.repositories.session_repository.SessionRepository.get_session", fake_get_session)
    monkeypatch.setattr("app.repositories.session_repository.SessionRepository.update_session", fake_update_session)
    monkeypatch.setattr("app.repositories.session_repository.SessionRepository.list_turns", fake_list_turns)
    monkeypatch.setattr("app.repositories.scenario_repository.ScenarioRepository.get", fake_get_scenario)
    monkeypatch.setattr("app.services.session_service.enqueue", fake_enqueue)

    websocket = AsyncMock()
    websocket.app = SimpleNamespace(state=SimpleNamespace(mongodb=MagicMock()))
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock()

    receive_started = asyncio.Event()

    async def fake_receive():
        if not receive_started.is_set():
            receive_started.set()
            return {"type": "websocket.receive", "text": json.dumps({"type": "session.update", "session": {"send_opening": False}})}
        await asyncio.Future()

    websocket.receive = AsyncMock(side_effect=fake_receive)

    await e2e_routes.e2e_voice_socket(websocket, session.id)

    assert session.status == "ended"
    assert session.realtime_state == "ended"
    assert session.termination_reason == "upstream_finish"
    assert enqueue_calls == [session.id]
    terminal_updates = [payload for payload in updates if payload.get("status") == "ended"]
    assert len(terminal_updates) == 1


@pytest.mark.asyncio
async def test_realtime_opening_prompt_persists_to_history_detail(monkeypatch):
    from app.api.routes import e2e_socket as e2e_routes

    session_service._FINALIZE_LOCKS.clear()
    session_service._PENDING_EVALUATION_TASKS.clear()
    session_service._EVALUATION_ENQUEUED.clear()

    session = PracticeSessionRecord(
        id="507f1f77bcf86cd799439012",
        scenario_id="scenario-1",
        stub_user_id="pilot-user",
        user_id=None,
        language="en",
        opening_prompt=None,
        status="active",
        client_session_started_at="2026-01-01T00:00:00+00:00",
        started_at="2026-01-01T00:00:00+00:00",
        ended_at=None,
        total_duration_seconds=None,
        idle_limit_seconds=None,
        duration_limit_seconds=None,
        ws_channel="/ws/sessions/507f1f77bcf86cd799439012",
        objective_status="unknown",
        objective_reason=None,
        termination_reason=None,
        evaluation_id=None,
        mode="realtime",
        rtc_room_id=None,
        rtc_task_id=None,
        realtime_state=None,
    )

    def apply_update(record: PracticeSessionRecord, payload: dict) -> PracticeSessionRecord:
        data = record.__dict__.copy()
        mapping = {
            "status": "status",
            "terminationReason": "termination_reason",
            "endedAt": "ended_at",
            "mode": "mode",
            "rtcRoomId": "rtc_room_id",
            "rtcTaskId": "rtc_task_id",
            "realtimeState": "realtime_state",
            "openingPrompt": "opening_prompt",
        }
        for key, value in payload.items():
            field = mapping.get(key)
            if field:
                data[field] = value
        return PracticeSessionRecord(**data)

    async def fake_get_session(self, session_id: str):
        return session if session_id == session.id else None

    async def fake_update_session(self, session_id: str, payload: dict):
        nonlocal session
        if session_id != session.id:
            return None
        session = apply_update(session, payload)
        return session

    async def fake_list_turns(self, session_id: str):
        if session_id != session.id:
            return []
        return []

    async def fake_get_scenario(self, scenario_id: str):
        return SimpleNamespace(
            id=scenario_id,
            metadata={"title": "Test Scenario", "domain": "Feedback", "scenarioType": "Coaching"},
            context={"situation": "Test", "background": "Context", "setting": "Call"},
            simulation_config={
                "ai": {"name": "Coach", "role": "Coach"},
                "trainee": {"name": "Trainee", "role": "Trainee"},
                "conversationStart": {
                    "speakerRoleId": "trainee",
                    "initialPromptToUser": "Begin.",
                },
            },
            evaluation_config={},
            status="published",
        )

    class FakeUpstream:
        def __init__(self):
            self.sent: list[bytes] = []
            self._recv_packets = [
                _build_server_ack(1, {}),
                _build_server_ack(100, {}),
            ]

        async def send(self, packet: bytes):
            self.sent.append(packet)

        async def recv(self):
            return self._recv_packets.pop(0)

        def __aiter__(self):
            return self

        async def __anext__(self):
            await asyncio.Future()

    class FakeConnect:
        def __init__(self):
            self.upstream = FakeUpstream()

        async def __aenter__(self):
            return self.upstream

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _get_by_session(_session_id: str):
        return None

    class FakeEvaluationRepo:
        get_by_session = staticmethod(_get_by_session)

    monkeypatch.setattr(
        e2e_routes,
        "_load_e2e_config",
        lambda: E2EConfig(
            ws_url="wss://example.test/ws",
            app_id="app-id",
            access_key="token",
            model=None,
            resource_id="volc.speech.dialog",
            app_key="app-key",
            speaker=None,
        ),
    )
    monkeypatch.setattr(e2e_routes, "ws_connect", lambda *args, **kwargs: FakeConnect())
    monkeypatch.setattr("app.repositories.session_repository.SessionRepository.get_session", fake_get_session)
    monkeypatch.setattr("app.repositories.session_repository.SessionRepository.update_session", fake_update_session)
    monkeypatch.setattr("app.repositories.session_repository.SessionRepository.list_turns", fake_list_turns)
    monkeypatch.setattr("app.repositories.scenario_repository.ScenarioRepository.get", fake_get_scenario)

    app.dependency_overrides[history_routes._evaluation_repo] = lambda: FakeEvaluationRepo()

    websocket = AsyncMock()
    websocket.app = SimpleNamespace(state=SimpleNamespace(mongodb=MagicMock(), minio=None))
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock()
    websocket.receive = AsyncMock(
        side_effect=[
            {"type": "websocket.receive", "text": json.dumps({"type": "session.update", "session": {}})},
            {"type": "websocket.disconnect"},
        ]
    )

    try:
        await e2e_routes.e2e_voice_socket(websocket, session.id)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/sessions/{session.id}",
                params={"historyStepCount": 2},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["session"]["openingPrompt"] == "Begin."
        assert payload["session"]["mode"] == "realtime"
    finally:
        app.dependency_overrides.pop(history_routes._evaluation_repo, None)
