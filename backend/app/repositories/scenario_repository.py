from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bson import ObjectId

from app.clients.mongodb import MongoDBClient


@dataclass(frozen=True)
class Scenario:
    id: str
    metadata: dict[str, Any]
    context: dict[str, Any]
    simulation_config: dict[str, Any]
    evaluation_config: dict[str, Any]
    status: str


def _scenario_from_doc(doc: dict[str, Any]) -> Scenario:
    return Scenario(
        id=str(doc["_id"]),
        metadata=doc.get("metadata", {}),
        context=doc.get("context", {}),
        simulation_config=doc.get("simulationConfig", {}),
        evaluation_config=doc.get("evaluationConfig", {}),
        status=doc.get("status", ""),
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
            query["metadata.domain"] = category
        if search:
            query["$or"] = [
                {"metadata.title": {"$regex": search, "$options": "i"}},
                {"context.situation": {"$regex": search, "$options": "i"}},
            ]
        cursor = collection.find(query).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [_scenario_from_doc(doc) for doc in docs]

    async def get(self, scenario_id: str) -> Scenario | None:
        collection = await self._client.collection("Scenario")
        try:
            doc = await collection.find_one({"_id": ObjectId(scenario_id)})
        except Exception:
            return None
        if doc is None:
            return None
        return _scenario_from_doc(doc)
