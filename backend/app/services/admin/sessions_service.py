from __future__ import annotations

import asyncio

from fastapi import HTTPException, status

from app.clients.leancloud import LeanCloudClient, LeanCloudError
from app.config import load_settings
from app.repositories.admin_scenario_repository import AdminScenarioRepository
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


def _scenario_repo() -> AdminScenarioRepository:
    return AdminScenarioRepository(_client())


def _admin_id(token: str | None) -> str:
    return token or "admin"


def _response(
    record: PracticeSessionRecord, scenario_title: str | None = None
) -> dict[str, str | None]:
    return {
        "id": record.id,
        "scenarioId": record.scenario_id,
        "scenarioTitle": scenario_title,
        "status": record.status,
        "startedAt": record.started_at,
        "endedAt": record.ended_at,
        "terminationReason": record.termination_reason,
        "evaluationStatus": record.objective_status,
    }


class AdminSessionsService:
    def __init__(
        self,
        repo: SessionRepository | None = None,
        scenario_repo: AdminScenarioRepository | None = None,
    ) -> None:
        self.repo = repo or _repo()
        self.scenario_repo = scenario_repo or _scenario_repo()

    async def _scenario_titles(self, scenario_ids: list[str]) -> dict[str, str]:
        unique_ids = {sid for sid in scenario_ids if sid}
        if not unique_ids:
            return {}
        results = await asyncio.gather(
            *(self.scenario_repo.get(sid) for sid in unique_ids),
            return_exceptions=True,
        )
        title_map: dict[str, str] = {}
        for record in results:
            if isinstance(record, Exception) or record is None:
                continue
            title = record.title
            if record.id and title:
                title_map[record.id] = title
        return title_map

    async def list_sessions(self) -> list[dict[str, str | None]]:
        sessions = await self.repo.list_sessions()
        scenario_map = await self._scenario_titles([s.scenario_id for s in sessions])
        return [_response(s, scenario_map.get(s.scenario_id)) for s in sessions]

    async def get_session(self, session_id: str) -> dict[str, str | None]:
        session = await self.repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        scenario = None
        if session.scenario_id:
            scenario = await self.scenario_repo.get(session.scenario_id)
        return _response(session, scenario.title if scenario else None)

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
