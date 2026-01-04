from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.clients.leancloud import LeanCloudClient, LeanCloudError


class ConflictError(Exception):
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


def _from_lc(payload: dict[str, Any]) -> SkillRecord:
    return SkillRecord(
        id=payload.get("objectId", ""),
        name=payload.get("name", ""),
        category=payload.get("category", ""),
        rubric=payload.get("rubric", ""),
        description=payload.get("description"),
        status=payload.get("status", "active"),
        version=payload.get("updatedAt"),
    )


class AdminSkillRepository:
    def __init__(self, client: LeanCloudClient) -> None:
        self._client = client

    async def list_skills(self, *, include_deleted: bool = False) -> list[SkillRecord]:
        where: dict[str, Any] = {}
        if not include_deleted:
            where["status"] = {"$ne": "deleted"}
        response = await self._client.get_json(
            "/1.1/classes/Skill",
            params={"where": json.dumps(where)},
        )
        results = response.get("results", [])
        return [_from_lc(item) for item in results]

    async def get_skill(self, skill_id: str) -> SkillRecord | None:
        try:
            payload = await self._client.get_json(f"/1.1/classes/Skill/{skill_id}")
        except LeanCloudError:
            return None
        return _from_lc(payload)

    async def create_skill(self, payload: dict[str, Any]) -> SkillRecord:
        data = {"status": "active", **payload}
        response = await self._client.post_json("/1.1/classes/Skill", data)
        record = data | response
        return _from_lc(record)

    async def update_skill(
        self,
        skill_id: str,
        payload: dict[str, Any],
        *,
        expected_version: str | None = None,
    ) -> SkillRecord:
        current = await self.get_skill(skill_id)
        if not current:
            raise LeanCloudError("Skill not found", status_code=404)
        if expected_version and current.version and expected_version != current.version:
            raise ConflictError("Skill has changed; refresh and retry")
        response = await self._client.put_json(
            f"/1.1/classes/Skill/{skill_id}", payload
        )
        record = {"objectId": skill_id, **payload, **response}
        updated = await self.get_skill(skill_id)
        return updated or _from_lc(record)

    async def soft_delete_skill(self, skill_id: str) -> None:
        await self._client.put_json(
            f"/1.1/classes/Skill/{skill_id}", {"status": "deleted"}
        )

    async def restore_skill(self, skill_id: str) -> SkillRecord | None:
        try:
            await self._client.put_json(
                f"/1.1/classes/Skill/{skill_id}", {"status": "active"}
            )
        except LeanCloudError:
            return None
        return await self.get_skill(skill_id)
