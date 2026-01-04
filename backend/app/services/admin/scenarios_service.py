from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.clients.leancloud import LeanCloudClient, LeanCloudError
import httpx
from app.config import load_settings
from app.repositories.admin_scenario_repository import (
    AdminScenarioRecord,
    AdminScenarioRepository,
    ConflictError,
)
from app.repositories.session_repository import SessionRepository
from app.services.audit_log_service import record_audit_entry


def _client() -> LeanCloudClient:
    settings = load_settings()
    return LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )


def _scenario_repo() -> AdminScenarioRepository:
    return AdminScenarioRepository(_client())


def _session_repo() -> SessionRepository:
    return SessionRepository(_client())


def _admin_id(token: str | None) -> str:
    return token or "admin"


def _validate_required(data: dict[str, Any]) -> None:
    required = [
        "category",
        "title",
        "description",
        "objective",
        "aiPersona",
        "traineePersona",
        "endCriteria",
        "skills",
        "prompt",
    ]
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required fields: {', '.join(missing)}",
        )
    if not isinstance(data.get("skills"), list) or len(data.get("skills", [])) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one skill is required",
        )


def _record_to_payload(record: AdminScenarioRecord) -> dict[str, Any]:
    return {
        "category": record.category,
        "title": record.title,
        "description": record.description,
        "objective": record.objective,
        "aiPersona": record.ai_persona,
        "traineePersona": record.trainee_persona,
        "endCriteria": record.end_criteria,
        "skills": record.skills,
        "prompt": record.prompt,
        "status": record.status,
    }


class AdminScenariosService:
    def __init__(
        self,
        repo: AdminScenarioRepository | None = None,
        session_repo: SessionRepository | None = None,
    ) -> None:
        self.repo = repo or _scenario_repo()
        self.session_repo = session_repo or _session_repo()

    async def list_scenarios(self, include_deleted: bool = False) -> list[AdminScenarioRecord]:
        return await self.repo.list_scenarios(include_deleted=include_deleted)

    async def get_scenario(self, scenario_id: str) -> AdminScenarioRecord:
        scenario = await self.repo.get(scenario_id)
        if not scenario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return scenario

    async def create_scenario(self, data: dict[str, Any], *, admin_token: str | None) -> AdminScenarioRecord:
        _validate_required(data)
        try:
            record = await self.repo.create(data)
            await record_audit_entry(
                admin_id=_admin_id(admin_token),
                action="create",
                entity_type="scenario",
                entity_id=record.id,
                details=f"Created scenario {record.title}",
            )
            return record
        except LeanCloudError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def update_scenario(
        self,
        scenario_id: str,
        data: dict[str, Any],
        *,
        expected_version: str | None,
        admin_token: str | None,
    ) -> AdminScenarioRecord:
        _validate_required(data)
        try:
            record = await self.repo.update(scenario_id, data, expected_version=expected_version)
            await record_audit_entry(
                admin_id=_admin_id(admin_token),
                action="update",
                entity_type="scenario",
                entity_id=scenario_id,
                details=f"Updated scenario {scenario_id}",
            )
            return record
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except LeanCloudError as exc:
            if exc.status_code == 404:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found") from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def publish(self, scenario_id: str, *, admin_token: str | None) -> AdminScenarioRecord:
        scenario = await self.get_scenario(scenario_id)
        _validate_required(_record_to_payload(scenario))
        record = await self.repo.update(scenario_id, {"status": "published"}, expected_version=scenario.version)
        await record_audit_entry(
            admin_id=_admin_id(admin_token),
            action="publish",
            entity_type="scenario",
            entity_id=scenario_id,
            details=f"Published scenario {scenario_id}",
        )
        return record

    async def unpublish(self, scenario_id: str, *, admin_token: str | None) -> AdminScenarioRecord:
        scenario = await self.get_scenario(scenario_id)
        record = await self.repo.update(scenario_id, {"status": "draft"}, expected_version=scenario.version)
        await record_audit_entry(
            admin_id=_admin_id(admin_token),
            action="unpublish",
            entity_type="scenario",
            entity_id=scenario_id,
            details=f"Unpublished scenario {scenario_id}",
        )
        return record

    async def soft_delete_scenario(self, scenario_id: str, *, admin_token: str | None) -> None:
        # Block deletion if sessions exist
        sessions = await self.session_repo.list_sessions()
        if any(session.scenario_id == scenario_id for session in sessions):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scenario has sessions")
        try:
            await self.repo.soft_delete(scenario_id)
            await record_audit_entry(
                admin_id=_admin_id(admin_token),
                action="delete",
                entity_type="scenario",
                entity_id=scenario_id,
                details=f"Soft deleted scenario {scenario_id}",
            )
        except LeanCloudError as exc:
            if exc.status_code == 404:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found") from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scenario has sessions") from exc

    async def restore_scenario(self, scenario_id: str, *, admin_token: str | None) -> AdminScenarioRecord:
        record = await self.repo.restore(scenario_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await record_audit_entry(
            admin_id=_admin_id(admin_token),
            action="restore",
            entity_type="scenario",
            entity_id=scenario_id,
            details=f"Restored scenario {scenario_id}",
        )
        return record
