from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from bson import ObjectId

from app.clients.mongodb import MongoDBClient


class ConflictError(Exception):
    pass


@dataclass(frozen=True)
class AdminScenarioRecord:
    id: str
    metadata: dict[str, Any]
    context: dict[str, Any]
    simulationConfig: dict[str, Any]
    evaluationConfig: dict[str, Any]
    status: str
    record_status: str
    version: str | None


def _from_doc(doc: dict[str, Any]) -> AdminScenarioRecord:
    return AdminScenarioRecord(
        id=str(doc.get("_id", "")),
        metadata=doc.get("metadata", {}),
        context=doc.get("context", {}),
        simulationConfig=doc.get("simulationConfig", {}),
        evaluationConfig=doc.get("evaluationConfig", {}),
        status=doc.get("status", "draft"),
        record_status=doc.get("recordStatus", doc.get("status", "active")),
        version=_version_from_doc(doc),
    )


def _version_from_doc(doc: dict[str, Any]) -> str:
    updated = doc.get("updatedAt")
    if updated:
        return str(updated)
    oid = doc.get("_id")
    if isinstance(oid, ObjectId):
        return oid.generation_time.isoformat()
    return str(oid)


class AdminScenarioRepository:
    def __init__(self, client: MongoDBClient) -> None:
        self._client = client

    async def list_scenarios(self, include_deleted: bool = False) -> list[AdminScenarioRecord]:
        collection = await self._client.collection("Scenario")
        query: dict[str, Any] = {}
        if not include_deleted:
            query["recordStatus"] = {"$ne": "deleted"}
        cursor = collection.find(query)
        docs = await cursor.to_list(length=None)
        return [_from_doc(doc) for doc in docs]

    async def get(self, scenario_id: str) -> AdminScenarioRecord | None:
        collection = await self._client.collection("Scenario")
        try:
            doc = await collection.find_one({"_id": ObjectId(scenario_id)})
        except Exception:
            return None
        if doc is None:
            return None
        return _from_doc(doc)

    async def create(self, payload: dict[str, Any]) -> AdminScenarioRecord:
        collection = await self._client.collection("Scenario")
        data = {"recordStatus": "active", **payload}
        result = await collection.insert_one(data)
        doc = {**data, "_id": result.inserted_id}
        return _from_doc(doc)

    async def update(
        self,
        scenario_id: str,
        payload: dict[str, Any],
        *,
        expected_version: str | None,
    ) -> AdminScenarioRecord:
        collection = await self._client.collection("Scenario")
        current = await self.get(scenario_id)
        if not current:
            raise Exception("Scenario not found")
        if expected_version and current.version and expected_version != current.version:
            raise ConflictError("Scenario has changed; refresh and retry")
        await collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$set": {**payload, "updatedAt": datetime.datetime.utcnow().isoformat()}}
        )
        updated = await self.get(scenario_id)
        if updated:
            return updated
        # Fallback if get fails after update
        doc = {"_id": ObjectId(scenario_id), **payload}
        return _from_doc(doc)

    async def soft_delete(self, scenario_id: str) -> None:
        collection = await self._client.collection("Scenario")
        await collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$set": {"recordStatus": "deleted"}}
        )

    async def restore(self, scenario_id: str) -> AdminScenarioRecord | None:
        collection = await self._client.collection("Scenario")
        try:
            await collection.update_one(
                {"_id": ObjectId(scenario_id)},
                {"$set": {"recordStatus": "active"}}
            )
        except Exception:
            return None
        return await self.get(scenario_id)
