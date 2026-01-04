from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status

from app.api.deps.admin_auth import AdminAuth
from app.services.admin.sessions_service import AdminSessionsService

router = APIRouter(prefix="/sessions", tags=["admin-sessions"], dependencies=[AdminAuth])


def _service() -> AdminSessionsService:
    return AdminSessionsService()


@router.get("")
async def list_sessions(service: AdminSessionsService = Depends(_service)):
    return {"sessions": await service.list_sessions()}


@router.get("/{session_id}")
async def get_session(session_id: str, service: AdminSessionsService = Depends(_service)):
    return await service.get_session(session_id)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    service: AdminSessionsService = Depends(_service),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    await service.delete_session(session_id, admin_token=x_admin_token)
    return None
