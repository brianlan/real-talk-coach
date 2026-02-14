from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.clients.mongodb import MongoDBClient
from app.config import load_settings
from app.repositories.audit_log_repository import AuditLogRecord, AuditLogRepository


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def record_audit_entry(
    *,
    admin_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    details: str | None = None,
    timestamp: str | None = None,
    repo: AuditLogRepository | None = None,
) -> AuditLogRecord:
    settings = load_settings()
    resolved_admin_id = (
        admin_id
        or settings.admin_audit_admin_id
        or settings.admin_access_token
    )
    payload = {
        "adminId": resolved_admin_id,
        "action": action,
        "entityType": entity_type,
        "entityId": entity_id,
        "timestamp": timestamp or _now_iso(),
        "details": details,
    }
    if repo is not None:
        return await repo.create_entry(payload)
    mongo_connection_string = f"mongodb://{settings.mongo_host}:{settings.mongo_port}"
    client = MongoDBClient(connection_string=mongo_connection_string, database=settings.mongo_db)
    try:
        repository = AuditLogRepository(client)
        return await repository.create_entry(payload)
    finally:
        await client.close()


async def list_audit_entries(
    *,
    entity_type: str | None = None,
    admin_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    repo: AuditLogRepository | None = None,
) -> list[AuditLogRecord]:
    # Build query filter
    where: dict[str, Any] = {}
    if entity_type:
        where["entityType"] = entity_type
    if admin_id:
        where["adminId"] = admin_id
    if start_date or end_date:
        date_filter: dict[str, Any] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        where["timestamp"] = date_filter

    if repo is not None:
        return await repo.list_entries(params=where if where else None)

    # Create temporary MongoDB client
    settings = load_settings()
    mongo_connection_string = f"mongodb://{settings.mongo_host}:{settings.mongo_port}"
    client = MongoDBClient(connection_string=mongo_connection_string, database=settings.mongo_db)
    try:
        repository = AuditLogRepository(client)
        return await repository.list_entries(params=where if where else None)
    finally:
        await client.close()
