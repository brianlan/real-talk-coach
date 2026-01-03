from __future__ import annotations

from fastapi import HTTPException, status

from app.clients.leancloud import LeanCloudClient, LeanCloudError
from app.config import load_settings
from app.repositories.session_repository import SessionRepository, PracticeSessionRecord
from app.services.audit_log_service import record_audit_entry


def _client() -> LeanCloudClient:
    settings = load_settings()
    return LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )


def _repo() -> SessionRepository:
    return SessionRepository(_client())


def _admin_id(token: str | None) -> str:
    return token or "admin"


def _response(record: PracticeSessionRecord) -> dict[str, str | None]:
    return {
        "id": record.id,
        "scenarioId": record.scenario_id,
        "status": record.status,
        "startedAt": record.started_at,
        "endedAt": record.ended_at,
        "terminationReason": record.termination_reason,
        "evaluationStatus": record.objective_status,
    }


class AdminSessionsService:
    def __init__(self, repo: SessionRepository | None = None) -> None:
        self.repo = repo or _repo()

    async def list_sessions(self) -> list[dict[str, str | None]]:
        sessions = await self.repo.list_sessions()
        return [_response(s) for s in sessions]

    async def get_session(self, session_id: str) -> dict[str, str | None]:
        session = await self.repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return _response(session)

    async def delete_session(self, session_id: str, *, admin_token: str | None) -> None:
        try:
            await self.repo.delete_session(session_id)
            await record_audit_entry(
                admin_id=_admin_id(admin_token),
                action="delete",
                entity_type="session",
                entity_id=session_id,
                details=f"Deleted session {session_id}",
            )
        except LeanCloudError as exc:
            if exc.status_code == 404:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc
