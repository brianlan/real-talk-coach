from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps.admin_auth import AdminAuth
from app.repositories.skill_repository import SkillRecord
from app.services.admin.skills_service import AdminSkillsService

router = APIRouter(prefix="/skills", tags=["admin-skills"], dependencies=[AdminAuth])


def _service() -> AdminSkillsService:
    return AdminSkillsService()


def _skill_response(record: SkillRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "category": record.category,
        "rubric": record.rubric,
        "description": record.description,
        "status": record.status,
        "version": record.version,
    }


@router.get("")
async def list_skills(
    include_deleted: bool = False,
    service: AdminSkillsService = Depends(_service),
):
    items = await service.list_skills(include_deleted=include_deleted)
    return {"skills": [_skill_response(item) for item in items]}


@router.get("/{skill_id}")
async def get_skill(skill_id: str, service: AdminSkillsService = Depends(_service)):
    record = await service.get_skill(skill_id)
    return _skill_response(record)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: dict[str, Any],
    service: AdminSkillsService = Depends(_service),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    record = await service.create_skill(payload, admin_token=x_admin_token)
    return _skill_response(record)


@router.put("/{skill_id}")
async def update_skill(
    skill_id: str,
    payload: dict[str, Any],
    service: AdminSkillsService = Depends(_service),
    if_match: str | None = Header(None, alias="If-Match"),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    if not if_match:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing If-Match header")
    record = await service.update_skill(
        skill_id,
        payload,
        expected_version=if_match,
        admin_token=x_admin_token,
    )
    return _skill_response(record)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: str,
    service: AdminSkillsService = Depends(_service),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    await service.soft_delete_skill(skill_id, admin_token=x_admin_token)
    return None


@router.post("/{skill_id}/restore")
async def restore_skill(
    skill_id: str,
    service: AdminSkillsService = Depends(_service),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    record = await service.restore_skill(skill_id, admin_token=x_admin_token)
    return _skill_response(record)
