from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.clients.leancloud import LeanCloudClient
from app.config import load_settings
from app.repositories.scenario_repository import ScenarioRepository

router = APIRouter()


def _repo() -> ScenarioRepository:
    settings = load_settings()
    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    return ScenarioRepository(client)


def _scenario_response(item):
    return {
        "id": item.id,
        "category": item.category,
        "title": item.title,
        "description": item.description,
        "objective": item.objective,
        "aiPersona": item.ai_persona,
        "traineePersona": item.trainee_persona,
        "endCriteria": item.end_criteria,
        "skills": item.skills,
        "skillSummaries": item.skill_summaries,
        "idleLimitSeconds": item.idle_limit_seconds,
        "durationLimitSeconds": item.duration_limit_seconds,
        "prompt": item.prompt,
    }


def _skill_response(item):
    return {
        "id": item.id,
        "externalId": item.external_id,
        "name": item.name,
        "category": item.category,
        "rubric": item.rubric,
        "description": item.description,
    }


@router.get("/scenarios")
async def list_scenarios(
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(20, le=100),
    repo: ScenarioRepository = Depends(_repo),
):
    items = await repo.list_published(category=category, search=search, limit=limit)
    return {"items": [_scenario_response(item) for item in items]}


@router.get("/skills")
async def list_skills(repo: ScenarioRepository = Depends(_repo)):
    items = await repo.list_skills()
    return {"items": [_skill_response(item) for item in items]}


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str, repo: ScenarioRepository = Depends(_repo)):
    scenario = await repo.get(scenario_id)
    if not scenario or scenario.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _scenario_response(scenario)
