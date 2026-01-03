from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuditLog:
    id: str
    admin_id: str
    action: str
    entity_type: str
    entity_id: str
    timestamp: str
    details: str | None = None
