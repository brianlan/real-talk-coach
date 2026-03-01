from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bson import ObjectId

from app.clients.mongodb import MongoDBClient


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


def _scenario_from_doc(doc: dict[str, Any], skill_map: dict[str, Skill]) -> Scenario:
    # Normalize skills to string IDs (handle potential ObjectId from MongoDB)
    raw_skills = doc.get("skills", [])
    skills = [str(skill_id) for skill_id in raw_skills]
    skill_summaries = []
    for skill_id in skills:
        skill = skill_map.get(skill_id)
        if not skill:
            continue
        skill_summaries.append(
            {"skillId": skill.id, "name": skill.name, "rubric": skill.rubric}
        )
    return Scenario(
        id=str(doc["_id"]),
        category=doc.get("category", ""),
        title=doc.get("title", ""),
        description=doc.get("description", ""),
        objective=doc.get("objective", ""),
        ai_persona=doc.get("aiPersona", {}),
        trainee_persona=doc.get("traineePersona", {}),
        end_criteria=doc.get("endCriteria", []),
        skills=skills,
        skill_summaries=skill_summaries,
        idle_limit_seconds=doc.get("idleLimitSeconds"),
        duration_limit_seconds=doc.get("durationLimitSeconds"),
        prompt=doc.get("prompt", ""),
        status=doc.get("status", ""),
    )


def _skill_from_doc(doc: dict[str, Any]) -> Skill:
    return Skill(
        id=str(doc["_id"]),
        external_id=doc.get("externalId", ""),
        name=doc.get("name", ""),
        category=doc.get("category", ""),
        rubric=doc.get("rubric", ""),
        description=doc.get("description"),
    )


class ScenarioRepository:
    def __init__(self, client: MongoDBClient) -> None:
        self._client = client

    async def list_published(
        self, *, category: str | None = None, search: str | None = None, limit: int = 20
    ) -> list[Scenario]:
        collection = await self._client.collection("Scenario")
        query: dict[str, Any] = {"status": "published"}
        if category:
            query["category"] = category
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"objective": {"$regex": search, "$options": "i"}},
            ]
        cursor = collection.find(query).limit(limit)
        docs = await cursor.to_list(length=limit)
        skills = await self.list_skills()
        skill_map = {skill.id: skill for skill in skills}
        return [_scenario_from_doc(doc, skill_map) for doc in docs]

    async def get(self, scenario_id: str) -> Scenario | None:
        collection = await self._client.collection("Scenario")
        try:
            doc = await collection.find_one({"_id": ObjectId(scenario_id)})
        except Exception:
            return None
        if doc is None:
            return None
        skills = await self.list_skills()
        skill_map = {skill.id: skill for skill in skills}
        return _scenario_from_doc(doc, skill_map)

    async def list_skills(self) -> list[Skill]:
        collection = await self._client.collection("Skill")
        cursor = collection.find({})
        docs = await cursor.to_list(length=None)
        return [_skill_from_doc(doc) for doc in docs]
