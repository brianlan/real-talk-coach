from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.clients.leancloud import LeanCloudClient


@dataclass(frozen=True)
class Scenario:
    id: str
    category: str
    title: str
    description: str
    objective: str
    ai_persona: dict[str, Any]
    trainee_persona: dict[str, Any]
    end_criteria: list[str]
    skills: list[str]
    skill_summaries: list[dict[str, Any]]
    idle_limit_seconds: int | None
    duration_limit_seconds: int | None
    prompt: str
    status: str


@dataclass(frozen=True)
class Skill:
    id: str
    external_id: str
    name: str
    category: str
    rubric: str
    description: str | None


def _scenario_from_lc(payload: dict[str, Any], skill_map: dict[str, Skill]) -> Scenario:
    skills = payload.get("skills", [])
    skill_summaries = []
    for skill_id in skills:
        skill = skill_map.get(skill_id)
        if not skill:
            continue
        skill_summaries.append(
            {"skillId": skill.id, "name": skill.name, "rubric": skill.rubric}
        )
    return Scenario(
        id=payload["objectId"],
        category=payload.get("category", ""),
        title=payload.get("title", ""),
        description=payload.get("description", ""),
        objective=payload.get("objective", ""),
        ai_persona=payload.get("aiPersona", {}),
        trainee_persona=payload.get("traineePersona", {}),
        end_criteria=payload.get("endCriteria", []),
        skills=skills,
        skill_summaries=skill_summaries,
        idle_limit_seconds=payload.get("idleLimitSeconds"),
        duration_limit_seconds=payload.get("durationLimitSeconds"),
        prompt=payload.get("prompt", ""),
        status=payload.get("status", ""),
    )


def _skill_from_lc(payload: dict[str, Any]) -> Skill:
    return Skill(
        id=payload["objectId"],
        external_id=payload.get("externalId", ""),
        name=payload.get("name", ""),
        category=payload.get("category", ""),
        rubric=payload.get("rubric", ""),
        description=payload.get("description"),
    )


class ScenarioRepository:
    def __init__(self, client: LeanCloudClient) -> None:
        self._client = client

    async def list_published(
        self, *, category: str | None = None, search: str | None = None, limit: int = 20
    ) -> list[Scenario]:
        where: dict[str, Any] = {"status": "published"}
        if category:
            where["category"] = category
        if search:
            where["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"objective": {"$regex": search, "$options": "i"}},
            ]
        response = await self._client.get_json(
            "/1.1/classes/Scenario",
            params={"where": json.dumps(where), "limit": limit},
        )
        scenarios_payload = response.get("results", [])
        skills = await self.list_skills()
        skill_map = {skill.id: skill for skill in skills}
        return [_scenario_from_lc(item, skill_map) for item in scenarios_payload]

    async def get(self, scenario_id: str) -> Scenario | None:
        try:
            payload = await self._client.get_json(f"/1.1/classes/Scenario/{scenario_id}")
        except Exception:
            return None
        skills = await self.list_skills()
        skill_map = {skill.id: skill for skill in skills}
        return _scenario_from_lc(payload, skill_map)

    async def list_skills(self) -> list[Skill]:
        response = await self._client.get_json("/1.1/classes/Skill")
        results = response.get("results", [])
        return [_skill_from_lc(item) for item in results]
