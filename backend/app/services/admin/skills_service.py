from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.clients.leancloud import LeanCloudClient, LeanCloudError
from app.config import load_settings
from app.repositories.skill_repository import AdminSkillRepository, ConflictError, SkillRecord
from app.services.audit_log_service import record_audit_entry


def _client() -> LeanCloudClient:
    settings = load_settings()
    return LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )


def _repo() -> AdminSkillRepository:
    return AdminSkillRepository(_client())


def _admin_id(token: str | None) -> str:
    # In absence of user identity, use token as surrogate admin identifier
    return token or "admin"


class AdminSkillsService:
    def __init__(self, repo: AdminSkillRepository | None = None) -> None:
        self.repo = repo or _repo()

    async def list_skills(self, include_deleted: bool = False) -> list[SkillRecord]:
        return await self.repo.list_skills(include_deleted=include_deleted)

    async def get_skill(self, skill_id: str) -> SkillRecord:
        skill = await self.repo.get_skill(skill_id)
        if not skill:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
        return skill

    async def create_skill(self, data: dict[str, Any], *, admin_token: str | None) -> SkillRecord:
        try:
            record = await self.repo.create_skill(data)
            await record_audit_entry(
                admin_id=_admin_id(admin_token),
                action="create",
                entity_type="skill",
                entity_id=record.id,
                details=f"Created skill {record.name}",
            )
            return record
        except LeanCloudError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def update_skill(
        self,
        skill_id: str,
        data: dict[str, Any],
        *,
        expected_version: str | None,
        admin_token: str | None,
    ) -> SkillRecord:
        try:
            record = await self.repo.update_skill(skill_id, data, expected_version=expected_version)
            await record_audit_entry(
                admin_id=_admin_id(admin_token),
                action="update",
                entity_type="skill",
                entity_id=skill_id,
                details=f"Updated skill {skill_id}",
            )
            return record
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except LeanCloudError as exc:
            if exc.status_code == 404:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found") from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def soft_delete_skill(self, skill_id: str, *, admin_token: str | None) -> None:
        try:
            await self.repo.soft_delete_skill(skill_id)
            await record_audit_entry(
                admin_id=_admin_id(admin_token),
                action="delete",
                entity_type="skill",
                entity_id=skill_id,
                details=f"Soft deleted skill {skill_id}",
            )
        except LeanCloudError as exc:
            if exc.status_code == 404:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found") from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def restore_skill(self, skill_id: str, *, admin_token: str | None) -> SkillRecord:
        record = await self.repo.restore_skill(skill_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
        await record_audit_entry(
            admin_id=_admin_id(admin_token),
            action="restore",
            entity_type="skill",
            entity_id=skill_id,
            details=f"Restored skill {skill_id}",
        )
        return record
