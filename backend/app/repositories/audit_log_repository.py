from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.clients.leancloud import LeanCloudClient


@dataclass(frozen=True)
class AuditLogRecord:
    id: str
    admin_id: str
    action: str
    entity_type: str
    entity_id: str
    timestamp: str | None
    details: str | None


def _from_lc(payload: dict[str, Any]) -> AuditLogRecord:
    return AuditLogRecord(
        id=payload.get("objectId", ""),
        admin_id=payload.get("adminId", ""),
        action=payload.get("action", ""),
        entity_type=payload.get("entityType", ""),
        entity_id=payload.get("entityId", ""),
        timestamp=payload.get("timestamp"),
        details=payload.get("details"),
    )


class AuditLogRepository:
    def __init__(self, client: LeanCloudClient) -> None:
        self._client = client

    async def create_entry(self, payload: dict[str, Any]) -> AuditLogRecord:
        response = await self._client.post_json("/1.1/classes/AuditLog", payload)
        record = payload | response
        return _from_lc(record)

    async def list_entries(self, params: dict[str, Any] | None = None) -> list[AuditLogRecord]:
        response = await self._client.get_json(
            "/1.1/classes/AuditLog",
            params=params,
        )
        results = response.get("results", [])
        return [_from_lc(item) for item in results]
