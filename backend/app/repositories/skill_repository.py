from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bson import ObjectId

from app.clients.mongodb import MongoDBClient


class ConflictError(Exception):
    pass


class NotFoundError(Exception):
    pass


@dataclass(frozen=True)
class SkillRecord:
    id: str
    name: str
    category: str
    rubric: str
    description: str | None
    status: str
    version: str | None


def _from_doc(doc: dict[str, Any]) -> SkillRecord:
    return SkillRecord(
        id=str(doc.get("_id", "")),
        name=doc.get("name", ""),
        category=doc.get("category", ""),
        rubric=doc.get("rubric", ""),
        description=doc.get("description"),
        status=doc.get("status", "active"),
        version=doc.get("updatedAt"),
    )


class AdminSkillRepository:
    def __init__(self, client: MongoDBClient) -> None:
        self._client = client

    async def list_skills(self, *, include_deleted: bool = False) -> list[SkillRecord]:
        collection = await self._client.collection("Skill")
        query: dict[str, Any] = {}
        if not include_deleted:
            query["status"] = {"$ne": "deleted"}
        cursor = collection.find(query)
        results = await cursor.to_list(length=None)
        return [_from_doc(item) for item in results]

    async def get_skill(self, skill_id: str) -> SkillRecord | None:
        collection = await self._client.collection("Skill")
        try:
            doc = await collection.find_one({"_id": ObjectId(skill_id)})
        except Exception:
            return None
        if doc is None:
            return None
        return _from_doc(doc)

    async def create_skill(self, payload: dict[str, Any]) -> SkillRecord:
        collection = await self._client.collection("Skill")
        data = {"status": "active", **payload}
        result = await collection.insert_one(data)
        doc = {**data, "_id": result.inserted_id}
        return _from_doc(doc)

    async def update_skill(
        self,
        skill_id: str,
        payload: dict[str, Any],
        *,
        expected_version: str | None = None,
    ) -> SkillRecord:
        current = await self.get_skill(skill_id)
        if not current:
            raise NotFoundError("Skill not found")
        if expected_version and current.version and expected_version != current.version:
            raise ConflictError("Skill has changed; refresh and retry")
        collection = await self._client.collection("Skill")
        await collection.update_one(
            {"_id": ObjectId(skill_id)},
            {"$set": payload},
        )
        updated = await self.get_skill(skill_id)
        if updated is None:
            raise NotFoundError("Skill not found after update")
        return updated

    async def soft_delete_skill(self, skill_id: str) -> None:
        collection = await self._client.collection("Skill")
        await collection.update_one(
            {"_id": ObjectId(skill_id)},
            {"$set": {"status": "deleted"}},
        )

    async def restore_skill(self, skill_id: str) -> SkillRecord | None:
        collection = await self._client.collection("Skill")
        try:
            await collection.update_one(
                {"_id": ObjectId(skill_id)},
                {"$set": {"status": "active"}},
            )
        except Exception:
            return None
        return await self.get_skill(skill_id)
