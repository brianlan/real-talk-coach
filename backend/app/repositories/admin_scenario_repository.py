from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.clients.leancloud import LeanCloudClient, LeanCloudError


class ConflictError(Exception):
    pass


@dataclass(frozen=True)
class AdminScenarioRecord:
    id: str
    category: str
    title: str
    description: str
    objective: str
    ai_persona: dict[str, Any]
    trainee_persona: dict[str, Any]
    end_criteria: list[str]
    skills: list[str]
    prompt: str
    status: str
    record_status: str
    idle_limit_seconds: int | None
    duration_limit_seconds: int | None
    version: str | None


def _from_lc(payload: dict[str, Any]) -> AdminScenarioRecord:
    return AdminScenarioRecord(
        id=payload.get("objectId", ""),
        category=payload.get("category", ""),
        title=payload.get("title", ""),
        description=payload.get("description", ""),
        objective=payload.get("objective", ""),
        ai_persona=payload.get("aiPersona", {}),
        trainee_persona=payload.get("traineePersona", {}),
        end_criteria=payload.get("endCriteria", []),
        skills=payload.get("skills", []),
        prompt=payload.get("prompt", ""),
        status=payload.get("status", "draft"),
        record_status=payload.get("recordStatus", payload.get("status", "active")),
        idle_limit_seconds=payload.get("idleLimitSeconds"),
        duration_limit_seconds=payload.get("durationLimitSeconds"),
        version=payload.get("updatedAt"),
    )


class AdminScenarioRepository:
    def __init__(self, client: LeanCloudClient) -> None:
        self._client = client

    async def list_scenarios(self, include_deleted: bool = False) -> list[AdminScenarioRecord]:
        where: dict[str, Any] = {}
        if not include_deleted:
            where["recordStatus"] = {"$ne": "deleted"}
        response = await self._client.get_json(
            "/1.1/classes/Scenario",
            params={"where": json.dumps(where)},
        )
        results = response.get("results", [])
        return [_from_lc(item) for item in results]

    async def get(self, scenario_id: str) -> AdminScenarioRecord | None:
        try:
            payload = await self._client.get_json(f"/1.1/classes/Scenario/{scenario_id}")
        except LeanCloudError:
            return None
        return _from_lc(payload)

    async def create(self, payload: dict[str, Any]) -> AdminScenarioRecord:
        data = {"recordStatus": "active", **payload}
        response = await self._client.post_json("/1.1/classes/Scenario", data)
        record = data | response
        return _from_lc(record)

    async def update(
        self,
        scenario_id: str,
        payload: dict[str, Any],
        *,
        expected_version: str | None,
    ) -> AdminScenarioRecord:
        current = await self.get(scenario_id)
        if not current:
            raise LeanCloudError("Scenario not found", status_code=404)
        if expected_version and current.version and expected_version != current.version:
            raise ConflictError("Scenario has changed; refresh and retry")
        response = await self._client.put_json(
            f"/1.1/classes/Scenario/{scenario_id}", payload
        )
        record = {"objectId": scenario_id, **payload, **response}
        updated = await self.get(scenario_id)
        return updated or _from_lc(record)

    async def soft_delete(self, scenario_id: str) -> None:
        await self._client.put_json(
            f"/1.1/classes/Scenario/{scenario_id}", {"recordStatus": "deleted"}
        )

    async def restore(self, scenario_id: str) -> AdminScenarioRecord | None:
        try:
            await self._client.put_json(
                f"/1.1/classes/Scenario/{scenario_id}", {"recordStatus": "active"}
            )
        except LeanCloudError:
            return None
        return await self.get(scenario_id)
