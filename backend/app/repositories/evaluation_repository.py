from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.clients.leancloud import LeanCloudClient, LeanCloudError


@dataclass(frozen=True)
class EvaluationRecord:
    id: str
    session_id: str
    status: str
    scores: list[dict[str, Any]]
    summary: str | None
    evaluator_model: str
    attempts: int
    last_error: str | None
    queued_at: str | None
    completed_at: str | None


def _evaluation_from_lc(payload: dict[str, Any]) -> EvaluationRecord:
    return EvaluationRecord(
        id=payload["objectId"],
        session_id=payload.get("sessionId", ""),
        status=payload.get("status", "pending"),
        scores=payload.get("scores", []) or [],
        summary=_normalize_summary(payload.get("summary")),
        evaluator_model=payload.get("evaluatorModel", ""),
        attempts=int(payload.get("attempts", 0) or 0),
        last_error=_normalize_last_error(payload.get("lastError")),
        queued_at=_normalize_date(payload.get("queuedAt")),
        completed_at=_normalize_date(payload.get("completedAt")),
    )


def _normalize_last_error(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("message") or raw.get("error")
    if isinstance(raw, str):
        return raw
    return None


def _normalize_summary(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("value") or raw.get("summary")
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


def _coerce_last_error(payload: dict[str, Any]) -> dict[str, Any]:
    updated = dict(payload)
    value = updated.get("lastError")
    if isinstance(value, str):
        updated["lastError"] = {"message": value}
    return updated


def _coerce_summary(payload: dict[str, Any]) -> dict[str, Any]:
    updated = dict(payload)
    value = updated.get("summary")
    if isinstance(value, str):
        updated["summary"] = {"value": value}
    return updated


def _retry_payloads(
    payload: dict[str, Any],
    field: str | None,
    expected: str | None,
    date_fields: list[str],
) -> list[dict[str, Any]]:
    retries: list[dict[str, Any]] = []
    if field in date_fields and expected in {"Object", "Date"}:
        retries.append(_coerce_dates(payload, date_fields, expected_type=expected))
        if expected == "Object":
            retries.append(_coerce_dates(payload, date_fields, expected_type="Date"))
    if field == "summary" and expected == "Object":
        retries.append(_coerce_summary(payload))
    if field == "lastError" and expected == "Object":
        retries.append(_coerce_last_error(payload))
    return retries


class EvaluationRepository:
    def __init__(self, client: LeanCloudClient) -> None:
        self._client = client

    async def create_evaluation(self, payload: dict[str, Any]) -> EvaluationRecord:
        normalized = dict(payload)
        date_fields = ["queuedAt", "completedAt"]
        candidates = [normalized]
        last_error: Exception | None = None
        while candidates:
            current = candidates.pop(0)
            try:
                response = await self._client.post_json(
                    "/1.1/classes/Evaluation", current
                )
                record = current | response
                return _evaluation_from_lc(record)
            except LeanCloudError as exc:
                last_error = exc
                field, expected = _parse_error_details(exc)
                retries = _retry_payloads(current, field, expected, date_fields)
                candidates = retries + candidates
                if not candidates:
                    break
        if last_error:
            raise last_error
        raise LeanCloudError("Evaluation create failed")

    async def update_evaluation(
        self, evaluation_id: str, payload: dict[str, Any]
    ) -> EvaluationRecord | None:
        normalized = dict(payload)
        date_fields = ["queuedAt", "completedAt"]
        candidates = [normalized]
        last_error: Exception | None = None
        while candidates:
            current = candidates.pop(0)
            try:
                response = await self._client.put_json(
                    f"/1.1/classes/Evaluation/{evaluation_id}", current
                )
                record = current | response | {"objectId": evaluation_id}
                return _evaluation_from_lc(record)
            except LeanCloudError as exc:
                last_error = exc
                field, expected = _parse_error_details(exc)
                retries = _retry_payloads(current, field, expected, date_fields)
                candidates = retries + candidates
                if not candidates:
                    break
            except Exception as exc:
                last_error = exc
                break
        if last_error:
            print(
                f"update_evaluation failed evaluation_id={evaluation_id} error={last_error}"
            )
        return None

    async def get_by_session(self, session_id: str) -> EvaluationRecord | None:
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
        params = {"where": json.dumps(where), "limit": 1}
        try:
            response = await self._client.get_json("/1.1/classes/Evaluation", params=params)
        except LeanCloudError as exc:
            if exc.status_code == 404 and exc.body:
                try:
                    payload = json.loads(exc.body)
                except json.JSONDecodeError:
                    payload = {}
                if payload.get("code") == 101:
                    return None
            raise
        results = response.get("results", [])
        if not results:
            return None
        return _evaluation_from_lc(results[0])
