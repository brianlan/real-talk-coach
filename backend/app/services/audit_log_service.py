from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from app.clients.leancloud import LeanCloudClient
from app.config import load_settings
from app.repositories.audit_log_repository import AuditLogRecord, AuditLogRepository


def _client() -> LeanCloudClient:
    settings = load_settings()
    return LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )


def _repo() -> AuditLogRepository:
    return AuditLogRepository(_client())


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
    repository = repo or _repo()
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
    return await repository.create_entry(payload)


async def list_audit_entries(
    *,
    entity_type: str | None = None,
    admin_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    repo: AuditLogRepository | None = None,
) -> list[AuditLogRecord]:
    repository = repo or _repo()
    where: dict[str, Any] = {}
    if entity_type:
        where["entityType"] = entity_type
    if admin_id:
        where["adminId"] = admin_id
    if start_date or end_date:
        created_at_filter: dict[str, Any] = {}
        if start_date:
            created_at_filter["$gte"] = {"__type": "Date", "iso": start_date}
        if end_date:
            created_at_filter["$lte"] = {"__type": "Date", "iso": end_date}
        where["timestamp"] = created_at_filter
    params = {"where": json.dumps(where)} if where else None
    return await repository.list_entries(params=params)
