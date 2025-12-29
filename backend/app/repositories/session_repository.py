from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.clients.leancloud import LeanCloudClient, LeanCloudError


@dataclass(frozen=True)
class PracticeSessionRecord:
    id: str
    scenario_id: str
    stub_user_id: str
    status: str
    client_session_started_at: str
    started_at: str | None
    ended_at: str | None
    total_duration_seconds: int | None
    idle_limit_seconds: int | None
    duration_limit_seconds: int | None
    ws_channel: str
    objective_status: str
    objective_reason: str | None
    termination_reason: str | None
    evaluation_id: str | None


@dataclass(frozen=True)
class TurnRecord:
    id: str
    session_id: str
    sequence: int
    speaker: str
    transcript: str | None
    audio_file_id: str
    audio_url: str | None
    asr_status: str | None
    created_at: str | None
    started_at: str | None
    ended_at: str | None
    context: str | None
    latency_ms: int | None


def _session_from_lc(payload: dict[str, Any]) -> PracticeSessionRecord:
    return PracticeSessionRecord(
        id=payload["objectId"],
        scenario_id=payload.get("scenarioId", ""),
        stub_user_id=payload.get("stubUserId", ""),
        status=payload.get("status", "pending"),
        client_session_started_at=payload.get("clientSessionStartedAt", ""),
        started_at=payload.get("startedAt"),
        ended_at=payload.get("endedAt"),
        total_duration_seconds=payload.get("totalDurationSeconds"),
        idle_limit_seconds=payload.get("idleLimitSeconds"),
        duration_limit_seconds=payload.get("durationLimitSeconds"),
        ws_channel=payload.get("wsChannel", ""),
        objective_status=payload.get("objectiveStatus", "unknown"),
        objective_reason=payload.get("objectiveReason"),
        termination_reason=payload.get("terminationReason"),
        evaluation_id=payload.get("evaluationId"),
    )


def _turn_from_lc(payload: dict[str, Any]) -> TurnRecord:
    return TurnRecord(
        id=payload["objectId"],
        session_id=payload.get("sessionId", ""),
        sequence=payload.get("sequence", 0),
        speaker=payload.get("speaker", ""),
        transcript=payload.get("transcript"),
        audio_file_id=payload.get("audioFileId", ""),
        audio_url=payload.get("audioUrl"),
        asr_status=payload.get("asrStatus"),
        created_at=payload.get("createdAt"),
        started_at=payload.get("startedAt"),
        ended_at=payload.get("endedAt"),
        context=payload.get("context"),
        latency_ms=payload.get("latencyMs"),
    )


class SessionRepository:
    def __init__(self, client: LeanCloudClient) -> None:
        self._client = client

    async def create_session(self, payload: dict[str, Any]) -> PracticeSessionRecord:
        response = await self._client.post_json("/1.1/classes/PracticeSession", payload)
        record = payload | response
        return _session_from_lc(record)

    async def get_session(self, session_id: str) -> PracticeSessionRecord | None:
        try:
            payload = await self._client.get_json(
                f"/1.1/classes/PracticeSession/{session_id}"
            )
        except Exception:
            return None
        return _session_from_lc(payload)

    async def update_session(
        self, session_id: str, payload: dict[str, Any]
    ) -> PracticeSessionRecord | None:
        try:
            response = await self._client.put_json(
                f"/1.1/classes/PracticeSession/{session_id}", payload
            )
        except Exception:
            return None
        record = payload | response | {"objectId": session_id}
        return _session_from_lc(record)

    async def add_turn(self, payload: dict[str, Any]) -> TurnRecord:
        defaults = {
            "audioUrl": "",
            "asrStatus": "not_applicable",
            "context": "",
            "latencyMs": -1,
        }
        normalized = {**defaults, **payload}
        for key, default in defaults.items():
            if normalized.get(key) is None:
                normalized[key] = default
        response = await self._client.post_json("/1.1/classes/Turn", normalized)
        record = normalized | response
        return _turn_from_lc(record)

    async def update_turn(self, turn_id: str, payload: dict[str, Any]) -> TurnRecord | None:
        try:
            response = await self._client.put_json(f"/1.1/classes/Turn/{turn_id}", payload)
        except Exception:
            return None
        record = payload | response | {"objectId": turn_id}
        return _turn_from_lc(record)

    async def list_turns(self, session_id: str) -> list[TurnRecord]:
        response = await self._client.get_json(
            "/1.1/classes/Turn", params={"where": json.dumps({"sessionId": session_id})}
        )
        results = response.get("results", [])
        return [_turn_from_lc(item) for item in results]

    async def get_turn(self, turn_id: str) -> TurnRecord | None:
        try:
            payload = await self._client.get_json(f"/1.1/classes/Turn/{turn_id}")
        except Exception:
            return None
        return _turn_from_lc(payload)

    async def list_sessions(self, stub_user_id: str | None = None) -> list[PracticeSessionRecord]:
        params = None
        if stub_user_id:
            params = {"where": json.dumps({"stubUserId": stub_user_id})}
        try:
            response = await self._client.get_json(
                "/1.1/classes/PracticeSession", params=params
            )
        except LeanCloudError as exc:
            if exc.status_code == 404 and exc.body:
                try:
                    payload = json.loads(exc.body)
                except json.JSONDecodeError:
                    payload = {}
                if payload.get("code") == 101:
                    return []
            raise
        results = response.get("results", [])
        return [_session_from_lc(item) for item in results]

    async def delete_session(self, session_id: str) -> None:
        await self._client.delete_json(f"/1.1/classes/PracticeSession/{session_id}")
