from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.clients.mongodb import MongoDBClient


@dataclass(frozen=True)
class AuditLogRecord:
    id: str
    admin_id: str
    action: str
    entity_type: str
    entity_id: str
    timestamp: str | None
    details: str | None


def _from_doc(doc: dict[str, Any]) -> AuditLogRecord:
    return AuditLogRecord(
        id=str(doc.get("_id", "")),
        admin_id=doc.get("adminId", ""),
        action=doc.get("action", ""),
        entity_type=doc.get("entityType", ""),
        entity_id=doc.get("entityId", ""),
        timestamp=doc.get("timestamp"),
        details=doc.get("details"),
    )


class AuditLogRepository:
    def __init__(self, client: MongoDBClient) -> None:
        self._client = client

    async def create_entry(self, payload: dict[str, Any]) -> AuditLogRecord:
        collection = await self._client.collection("AuditLog")
        result = await collection.insert_one(payload)
        doc = {**payload, "_id": result.inserted_id}
        return _from_doc(doc)

    async def list_entries(self, params: dict[str, Any] | None = None) -> list[AuditLogRecord]:
        collection = await self._client.collection("AuditLog")
        cursor = collection.find(params or {})
        results = await cursor.to_list(length=None)
        return [_from_doc(item) for item in results]
