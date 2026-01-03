from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps.admin_auth import AdminAuth
from app.services.admin.scenarios_service import AdminScenariosService
from app.repositories.admin_scenario_repository import AdminScenarioRecord

router = APIRouter(prefix="/scenarios", tags=["admin-scenarios"], dependencies=[AdminAuth])


def _service() -> AdminScenariosService:
    return AdminScenariosService()


def _response(record: AdminScenarioRecord) -> dict[str, Any]:
    return {
        "id": record.id,
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
        "recordStatus": record.record_status,
        "idleLimitSeconds": record.idle_limit_seconds,
        "durationLimitSeconds": record.duration_limit_seconds,
        "version": record.version,
    }


@router.get("")
async def list_scenarios(
    include_deleted: bool = False,
    service: AdminScenariosService = Depends(_service),
):
    items = await service.list_scenarios(include_deleted=include_deleted)
    return {"scenarios": [_response(item) for item in items]}


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str, service: AdminScenariosService = Depends(_service)):
    record = await service.get_scenario(scenario_id)
    return _response(record)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scenario(
    payload: dict[str, Any],
    service: AdminScenariosService = Depends(_service),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    record = await service.create_scenario(payload, admin_token=x_admin_token)
    return _response(record)


@router.put("/{scenario_id}")
async def update_scenario(
    scenario_id: str,
    payload: dict[str, Any],
    service: AdminScenariosService = Depends(_service),
    if_match: str | None = Header(None, alias="If-Match"),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    if not if_match:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing If-Match header")
    record = await service.update_scenario(
        scenario_id,
        payload,
        expected_version=if_match,
        admin_token=x_admin_token,
    )
    return _response(record)


@router.post("/{scenario_id}/publish")
async def publish_scenario(
    scenario_id: str,
    service: AdminScenariosService = Depends(_service),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    record = await service.publish(scenario_id, admin_token=x_admin_token)
    return _response(record)


@router.post("/{scenario_id}/unpublish")
async def unpublish_scenario(
    scenario_id: str,
    service: AdminScenariosService = Depends(_service),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    record = await service.unpublish(scenario_id, admin_token=x_admin_token)
    return _response(record)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: str,
    service: AdminScenariosService = Depends(_service),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    await service.soft_delete_scenario(scenario_id, admin_token=x_admin_token)
    return None


@router.post("/{scenario_id}/restore")
async def restore_scenario(
    scenario_id: str,
    service: AdminScenariosService = Depends(_service),
    x_admin_token: str | None = Header(None, convert_underscores=False),
):
    record = await service.restore_scenario(scenario_id, admin_token=x_admin_token)
    return _response(record)
