from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.clients.leancloud import LeanCloudClient, LeanCloudError


@dataclass(frozen=True)
class PracticeSessionRecord:
    id: str
    scenario_id: str
    stub_user_id: str
    language: str | None
    opening_prompt: str | None
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


def _normalize_termination_reason(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("reason") or raw.get("value")
    if isinstance(raw, str):
        return raw
    return None


def _normalize_evaluation_id(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("id") or raw.get("objectId")
    if isinstance(raw, str):
        return raw
    return None


def _normalize_opening_prompt(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("text") or raw.get("prompt")
    if isinstance(raw, str):
        return raw
    return None


def _normalize_date(raw: Any) -> str | None:
    if isinstance(raw, dict) and raw.get("__type") == "Date":
        return raw.get("iso")
    if isinstance(raw, dict):
        return raw.get("iso") or raw.get("value")
    if isinstance(raw, str):
        return raw
    return None


def _format_iso(value: str) -> str:
    try:
        if value.endswith("Z"):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _parse_error_details(exc: LeanCloudError) -> tuple[str | None, str | None]:
    if not exc.body:
        return None, None
    try:
        payload = json.loads(exc.body)
    except json.JSONDecodeError:
        return None, None
    error = payload.get("error")
    if not isinstance(error, str):
        return None, None
    field_match = re.search(r"field '([^']+)'", error)
    expected_match = re.search(r'expect type is [^\"]*\"([^\"]+)\"', error)
    field = field_match.group(1) if field_match else None
    expected = expected_match.group(1) if expected_match else None
    return field, expected


def _coerce_dates(
    payload: dict[str, Any], fields: list[str], *, expected_type: str | None = None
) -> dict[str, Any]:
    updated = dict(payload)
    for field in fields:
        value = updated.get(field)
        if isinstance(value, str):
            iso_value = _format_iso(value)
            if expected_type == "Date":
                updated[field] = {"__type": "Date", "iso": iso_value}
            else:
                updated[field] = {"value": iso_value}
    return updated


def _session_from_lc(payload: dict[str, Any]) -> PracticeSessionRecord:
    return PracticeSessionRecord(
        id=payload["objectId"],
        scenario_id=payload.get("scenarioId", ""),
        stub_user_id=payload.get("stubUserId", ""),
        language=payload.get("language"),
        opening_prompt=_normalize_opening_prompt(payload.get("openingPrompt")),
        status=payload.get("status", "pending"),
        client_session_started_at=_normalize_date(payload.get("clientSessionStartedAt"))
        or "",
        started_at=_normalize_date(payload.get("startedAt")),
        ended_at=_normalize_date(payload.get("endedAt")),
        total_duration_seconds=payload.get("totalDurationSeconds"),
        idle_limit_seconds=payload.get("idleLimitSeconds"),
        duration_limit_seconds=payload.get("durationLimitSeconds"),
        ws_channel=payload.get("wsChannel", ""),
        objective_status=payload.get("objectiveStatus", "unknown"),
        objective_reason=payload.get("objectiveReason"),
        termination_reason=_normalize_termination_reason(payload.get("terminationReason")),
        evaluation_id=_normalize_evaluation_id(payload.get("evaluationId")),
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
        created_at=_normalize_date(payload.get("createdAt")),
        started_at=_normalize_date(payload.get("startedAt")),
        ended_at=_normalize_date(payload.get("endedAt")),
        context=payload.get("context"),
        latency_ms=payload.get("latencyMs"),
    )


class SessionRepository:
    def __init__(self, client: LeanCloudClient) -> None:
        self._client = client

    async def create_session(self, payload: dict[str, Any]) -> PracticeSessionRecord:
        normalized = dict(payload)
        date_fields = [
            "clientSessionStartedAt",
            "startedAt",
            "endedAt",
        ]
        try:
            response = await self._client.post_json(
                "/1.1/classes/PracticeSession", normalized
            )
        except LeanCloudError as exc:
            field, expected = _parse_error_details(exc)
            if field in date_fields and expected in {"Object", "Date"}:
                normalized = _coerce_dates(
                    normalized, date_fields, expected_type=expected
                )
                response = await self._client.post_json(
                    "/1.1/classes/PracticeSession", normalized
                )
            else:
                raise
        record = normalized | response
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
        normalized = dict(payload)
        termination_reason = normalized.get("terminationReason")
        evaluation_id = normalized.get("evaluationId")
        retry_payload = None
        if isinstance(termination_reason, str):
            retry_payload = {
                **normalized,
                "terminationReason": {"reason": termination_reason},
            }
        if isinstance(evaluation_id, str):
            normalized["evaluationId"] = {"id": evaluation_id}
        date_fields = ["startedAt", "endedAt"]
        last_error: Exception | None = None
        for candidate in [normalized, retry_payload]:
            if candidate is None:
                continue
            try:
                response = await self._client.put_json(
                    f"/1.1/classes/PracticeSession/{session_id}", candidate
                )
                refreshed = await self.get_session(session_id)
                if refreshed:
                    return refreshed
                record = payload | response | {"objectId": session_id}
                return _session_from_lc(record)
            except LeanCloudError as exc:
                last_error = exc
                field, expected = _parse_error_details(exc)
                if field in date_fields and expected in {"Object", "Date"}:
                    try:
                        coerced = _coerce_dates(
                            candidate, date_fields, expected_type=expected
                        )
                        response = await self._client.put_json(
                            f"/1.1/classes/PracticeSession/{session_id}", coerced
                        )
                        refreshed = await self.get_session(session_id)
                        if refreshed:
                            return refreshed
                        record = payload | response | {"objectId": session_id}
                        return _session_from_lc(record)
                    except Exception as retry_exc:
                        last_error = retry_exc
            except Exception as exc:
                last_error = exc
        if last_error:
            print(f"update_session failed session_id={session_id} error={last_error}")
        return None

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
        date_fields = ["createdAt", "startedAt", "endedAt"]
        try:
            response = await self._client.post_json("/1.1/classes/Turn", normalized)
        except LeanCloudError as exc:
            field, expected = _parse_error_details(exc)
            if field in date_fields and expected in {"Object", "Date"}:
                normalized = _coerce_dates(
                    normalized, date_fields, expected_type=expected
                )
                response = await self._client.post_json("/1.1/classes/Turn", normalized)
            else:
                raise
        record = normalized | response
        return _turn_from_lc(record)

    async def update_turn(self, turn_id: str, payload: dict[str, Any]) -> TurnRecord | None:
        normalized = dict(payload)
        date_fields = ["createdAt", "startedAt", "endedAt"]
        try:
            response = await self._client.put_json(
                f"/1.1/classes/Turn/{turn_id}", normalized
            )
        except LeanCloudError as exc:
            field, expected = _parse_error_details(exc)
            if field in date_fields and expected in {"Object", "Date"}:
                try:
                    normalized = _coerce_dates(
                        normalized, date_fields, expected_type=expected
                    )
                    response = await self._client.put_json(
                        f"/1.1/classes/Turn/{turn_id}", normalized
                    )
                except Exception:
                    return None
            else:
                return None
        except Exception:
            return None
        record = normalized | response | {"objectId": turn_id}
        return _turn_from_lc(record)

    async def list_turns(self, session_id: str) -> list[TurnRecord]:
        where = {
            "$or": [
                {"sessionId": session_id},
                {
                    "sessionId": {
                        "__type": "Pointer",
                        "className": "PracticeSession",
                        "objectId": session_id,
                    }
                },
            ]
        }
        response = await self._client.get_json(
            "/1.1/classes/Turn",
            params={"where": json.dumps(where)},
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
