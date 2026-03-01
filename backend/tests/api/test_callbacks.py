"""Tests for Doubao callback webhook endpoint.

Tests POST /callbacks/doubao endpoint including:
- Transcript callback processing
- Interrupt callback processing
- Signature verification
- Invalid payload rejection
"""

import hmac
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.session_repository import SessionRepository, TurnRecord


# Test constants
TEST_CALLBACK_SECRET = "test-callback-secret-key"
TEST_SESSION_ID = "507f1f77bcf86cd799439011"
TEST_TASK_ID = "test-task-id-123"
TEST_ROOM_ID = "test-room-id-456"


def generate_signature(secret: str, body: bytes) -> str:
    """Generate HMAC-SHA256 signature for callback."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def create_mock_session(session_id: str = TEST_SESSION_ID):
    """Create a mock session object."""
    mock = MagicMock()
    mock.id = session_id
    mock.rtcTaskId = TEST_TASK_ID
    mock.rtcRoomId = TEST_ROOM_ID
    mock.status = "active"
    return mock


def create_mock_turn(turn_id: str, sequence: int = 1, speaker: str = "trainee"):
    """Create a mock turn record."""
    mock = MagicMock()
    mock.id = turn_id
    mock.sequence = sequence
    mock.speaker = speaker
    mock.transcript = ""
    mock.is_interrupted = False
    mock.asr_status = None
    return mock


@pytest.fixture
def mock_repo():
    """Create a mock SessionRepository."""
    repo = MagicMock()
    repo.get_session_by_rtc_task_id = AsyncMock(return_value=create_mock_session())
    repo.get_session_by_rtc_room_id = AsyncMock(return_value=create_mock_session())
    repo.list_turns = AsyncMock(return_value=[])
    repo.add_turn = AsyncMock(return_value=create_mock_turn("turn123"))
    repo.update_turn = AsyncMock(return_value=create_mock_turn("turn123"))
    repo.update_session = AsyncMock(return_value=create_mock_session())
    return repo


@pytest.fixture
def client(mock_repo):
    """Create test client with mocked repository."""
    from app.api.routes import callbacks

    app.state.mongodb = MagicMock()
    app.state.minio = None

    def override_get_repo():
        return mock_repo

    app.dependency_overrides[callbacks._repo] = override_get_repo
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def callback_url():
    """Return the callback endpoint URL."""
    return "/api/callbacks/doubao"


class TestSignatureVerification:
    """Tests for signature verification."""

    def test_valid_signature_accepts_request(self, client, callback_url, mock_repo):
        """Valid signature should result in 202 accepted."""
        payload = {
            "event": "transcript_update",
            "sessionId": TEST_SESSION_ID,
            "subtitleText": "Hello, this is a test.",
            "fromUserId": "user1",
            "RoundID": 0,
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["eventType"] == "transcript_update"

    def test_invalid_signature_rejects_request(self, client, callback_url, monkeypatch):
        """Invalid signature should result in 401 unauthorized."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        payload = {
            "event": "transcript_update",
            "sessionId": TEST_SESSION_ID,
            "subtitleText": "Test",
        }
        body = json.dumps(payload).encode("utf-8")
        invalid_signature = "invalid-signature-12345"

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": invalid_signature,
            },
        )

        assert response.status_code == 401
        assert "Invalid callback signature" in response.json()["detail"]

    def test_missing_signature_rejects_request(self, client, callback_url, monkeypatch):
        """Missing signature should result in 401 unauthorized."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        payload = {
            "event": "transcript_update",
            "sessionId": TEST_SESSION_ID,
        }
        body = json.dumps(payload).encode("utf-8")

        response = client.post(
            callback_url,
            content=body,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 401
        assert "Missing callback signature" in response.json()["detail"]

    def test_missing_secret_config_returns_503(self, client, callback_url, monkeypatch):
        """Missing VOLCENGINE_CALLBACK_SIGNATURE should return 503."""
        monkeypatch.delenv("VOLCENGINE_CALLBACK_SIGNATURE", raising=False)

        payload = {"event": "transcript_update", "sessionId": TEST_SESSION_ID}
        body = json.dumps(payload).encode("utf-8")

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": "any-signature",
            },
        )

        assert response.status_code == 503
        assert "Callback secret is not configured" in response.json()["detail"]


class TestTranscriptCallback:
    """Tests for transcript callback processing."""

    def test_transcript_callback_creates_turn(self, client, callback_url, mock_repo, monkeypatch):
        """Transcript callback should create a new turn."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        mock_repo.list_turns = AsyncMock(return_value=[])

        payload = {
            "event": "transcript_update",
            "sessionId": TEST_SESSION_ID,
            "subtitleText": "Hello, this is the trainee speaking.",
            "fromUserId": "user1",
            "RoundID": 1,
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["processed"] is True
        assert data["turnsCreated"] == 1
        mock_repo.add_turn.assert_called_once()

    def test_transcript_callback_updates_existing_turn(
        self, client, callback_url, mock_repo, monkeypatch
    ):
        """Transcript callback should update existing turn with same sequence."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        existing_turn = create_mock_turn("existing-turn-123", sequence=1, speaker="trainee")
        mock_repo.list_turns = AsyncMock(return_value=[existing_turn])

        payload = {
            "event": "transcript_update",
            "sessionId": TEST_SESSION_ID,
            "subtitleText": "Updated transcript text.",
            "fromUserId": "user1",
            "RoundID": 1,
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["turnsUpdated"] == 1
        mock_repo.update_turn.assert_called_once()

    def test_user_and_ai_transcript_callback(self, client, callback_url, mock_repo, monkeypatch):
        """Callback with both user and AI transcripts should create two turns."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)
        mock_repo.list_turns = AsyncMock(return_value=[])

        payload = {
            "event": "transcript_update",
            "sessionId": TEST_SESSION_ID,
            "userTranscript": "Trainee response here.",
            "aiTranscript": "AI response here.",
            "RoundID": 1,
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["turnsCreated"] == 2


class TestInterruptCallback:
    """Tests for interrupt callback processing."""

    def test_interrupt_callback_marks_turn_interrupted(
        self, client, callback_url, mock_repo, monkeypatch
    ):
        """Interrupt callback should mark the latest AI turn as interrupted."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        ai_turn = create_mock_turn("ai-turn-123", sequence=1, speaker="ai")
        ai_turn.is_interrupted = False
        mock_repo.list_turns = AsyncMock(return_value=[ai_turn])

        payload = {
            "event": "interrupt",
            "sessionId": TEST_SESSION_ID,
            "interrupt": True,
            "EventTime": 1700000000000,
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["processed"] is True

        # Verify update_turn was called with interrupt flags
        mock_repo.update_turn.assert_called_once()
        call_kwargs = mock_repo.update_turn.call_args[0][1]
        assert call_kwargs.get("isInterrupted") is True
        assert call_kwargs.get("interruptedAtMs") == 1700000000000


class TestConversationEndCallback:
    """Tests for conversation end callback processing."""

    def test_conversation_end_marks_session_ended(
        self, client, callback_url, mock_repo, monkeypatch
    ):
        """Conversation end callback should mark session as ended."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        payload = {
            "event": "conversation_end",
            "sessionId": TEST_SESSION_ID,
            "RunStage": "taskStop",
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["processed"] is True

        # Verify update_session was called with ended status
        mock_repo.update_session.assert_called_once()
        call_kwargs = mock_repo.update_session.call_args[0][1]
        assert call_kwargs.get("status") == "ended"
        assert call_kwargs.get("realtimeState") == "ended"


class TestInvalidPayload:
    """Tests for invalid payload handling."""

    def test_invalid_json_rejects_request(self, client, callback_url, monkeypatch):
        """Invalid JSON should result in 422 unprocessable entity."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        invalid_json = b"not valid json {"

        response = client.post(
            callback_url,
            content=invalid_json,
            headers={
                "Content-Type": "application/json",
                "X-Signature": generate_signature(TEST_CALLBACK_SECRET, invalid_json),
            },
        )

        assert response.status_code == 422
        assert "Invalid JSON payload" in response.json()["detail"]

    def test_missing_session_identity_rejects_request(
        self, client, callback_url, mock_repo, monkeypatch
    ):
        """Missing session identity should result in 422."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        # No sessionId, taskId, or roomId
        payload = {
            "event": "transcript_update",
            "subtitleText": "Test",
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        # Mock repo returns None for session lookup
        mock_repo.get_session_by_rtc_task_id = AsyncMock(return_value=None)
        mock_repo.get_session_by_rtc_room_id = AsyncMock(return_value=None)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 422
        assert "Missing session identity" in response.json()["detail"]


class TestSessionResolution:
    """Tests for session ID resolution from different sources."""

    def test_resolves_session_from_session_id(self, client, callback_url, mock_repo, monkeypatch):
        """Session should be resolved from sessionId field."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        payload = {
            "event": "transcript_update",
            "sessionId": TEST_SESSION_ID,
            "subtitleText": "Test transcript",
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 202
        # Should not try to resolve via task_id or room_id
        mock_repo.get_session_by_rtc_task_id.assert_not_called()
        mock_repo.get_session_by_rtc_room_id.assert_not_called()

    def test_resolves_session_from_task_id(self, client, callback_url, mock_repo, monkeypatch):
        """Session should be resolved from taskId when sessionId is missing."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        mock_repo.get_session_by_rtc_task_id = AsyncMock(
            return_value=create_mock_session()
        )

        payload = {
            "event": "transcript_update",
            "taskId": TEST_TASK_ID,
            "subtitleText": "Test transcript",
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 202
        mock_repo.get_session_by_rtc_task_id.assert_called_once_with(TEST_TASK_ID)

    def test_resolves_session_from_room_id(self, client, callback_url, mock_repo, monkeypatch):
        """Session should be resolved from roomId when sessionId and taskId are missing."""
        monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", TEST_CALLBACK_SECRET)

        mock_repo.get_session_by_rtc_task_id = AsyncMock(return_value=None)
        mock_repo.get_session_by_rtc_room_id = AsyncMock(
            return_value=create_mock_session()
        )

        payload = {
            "event": "transcript_update",
            "RoomId": TEST_ROOM_ID,
            "subtitleText": "Test transcript",
        }
        body = json.dumps(payload).encode("utf-8")
        signature = generate_signature(TEST_CALLBACK_SECRET, body)

        response = client.post(
            callback_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
            },
        )

        assert response.status_code == 202
        mock_repo.get_session_by_rtc_room_id.assert_called_once_with(TEST_ROOM_ID)
