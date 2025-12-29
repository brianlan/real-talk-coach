from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("app.telemetry")


def build_sc_attributes(sc_id: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    attributes = {"sc_id": sc_id}
    if extra:
        attributes.update(extra)
    return attributes


def build_event(
    name: str,
    *,
    session_id: str | None = None,
    turn_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "type": "event",
        "name": name,
        "sessionId": session_id,
        "turnId": turn_id,
        "attributes": attributes or {},
    }
    return payload


def emit_event(
    name: str,
    *,
    session_id: str | None = None,
    turn_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_event(
        name,
        session_id=session_id,
        turn_id=turn_id,
        attributes=attributes,
    )
    logger.info(json.dumps(payload, sort_keys=True))
    return payload


def build_metric(
    name: str,
    value: float,
    *,
    session_id: str | None = None,
    turn_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "type": "metric",
        "name": name,
        "value": value,
        "sessionId": session_id,
        "turnId": turn_id,
        "attributes": attributes or {},
    }
    return payload


def emit_metric(
    name: str,
    value: float,
    *,
    session_id: str | None = None,
    turn_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_metric(
        name,
        value,
        session_id=session_id,
        turn_id=turn_id,
        attributes=attributes,
    )
    logger.info(json.dumps(payload, sort_keys=True))
    return payload
