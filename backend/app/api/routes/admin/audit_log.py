from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.api.deps.admin_auth import AdminAuth
from app.repositories.audit_log_repository import AuditLogRecord
from app.services.audit_log_service import list_audit_entries

router = APIRouter(prefix="/audit-log", tags=["admin-audit"], dependencies=[AdminAuth])


def _entry_response(record: AuditLogRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "adminId": record.admin_id,
        "action": record.action,
        "entityType": record.entity_type,
        "entityId": record.entity_id,
        "timestamp": record.timestamp,
        "details": record.details,
    }


@router.get("")
async def list_audit_log_entries(
    entity_type: str | None = Query(None, alias="entityType"),
    admin_id: str | None = Query(None, alias="adminId"),
    start_date: str | None = Query(None, alias="startDate"),
    end_date: str | None = Query(None, alias="endDate"),
):
    entries = await list_audit_entries(
        entity_type=entity_type,
        admin_id=admin_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {"entries": [_entry_response(entry) for entry in entries]}
