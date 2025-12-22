from __future__ import annotations

import base64

import httpx
import pytest
from fastapi import status

from app.main import app


def _audio_payload(size_bytes: int) -> str:
    return base64.b64encode(b"a" * size_bytes).decode("ascii")


@pytest.mark.asyncio
async def test_turn_submission_contract():
    payload = {
        "sequence": 1,
        "audioBase64": _audio_payload(16),
        "startedAt": "2025-01-01T00:00:00Z",
        "endedAt": "2025-01-01T00:00:01Z",
    }

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/sessions/session-1/turns", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    receipt = response.json()
    assert receipt["sessionId"] == "session-1"
    assert "turnId" in receipt


@pytest.mark.asyncio
async def test_turn_rejects_oversized_audio():
    payload = {
        "sequence": 1,
        "audioBase64": _audio_payload(131073),
        "startedAt": "2025-01-01T00:00:00Z",
        "endedAt": "2025-01-01T00:00:01Z",
    }

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/sessions/session-1/turns", json=payload)

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    body = response.json()
    assert "128" in str(body).lower()
