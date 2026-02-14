from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bson.objectid import ObjectId

from app.clients.mongodb import MongoDBClient


@dataclass(frozen=True)
class EvaluationRecord:
    id: str
    session_id: str
    status: str
    scores: list[dict[str, Any]]
    summary: str | None
    evaluator_model: str
    attempts: int
    last_error: str | None
    queued_at: str | None
    completed_at: str | None


def _normalize_last_error(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("message") or raw.get("error")
    if isinstance(raw, str):
        return raw
    return None


def _normalize_summary(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("value") or raw.get("summary")
    if isinstance(raw, str):
        return raw
    return None


def _normalize_date(raw: Any) -> str | None:
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(raw, str):
        return raw
    return None


def _evaluation_from_doc(doc: dict[str, Any]) -> EvaluationRecord:
    return EvaluationRecord(
        id=str(doc.get("_id", "")),
        session_id=doc.get("sessionId", ""),
        status=doc.get("status", "pending"),
        scores=doc.get("scores", []) or [],
        summary=_normalize_summary(doc.get("summary")),
        evaluator_model=doc.get("evaluatorModel", ""),
        attempts=int(doc.get("attempts", 0) or 0),
        last_error=_normalize_last_error(doc.get("lastError")),
        queued_at=_normalize_date(doc.get("queuedAt")),
        completed_at=_normalize_date(doc.get("completedAt")),
    )


def _doc_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert payload to MongoDB document, handling date fields."""
    doc = dict(payload)

    # Handle date fields - store as datetime objects
    date_fields = ["queuedAt", "completedAt"]
    for field in date_fields:
        if field in doc and isinstance(doc[field], str):
            try:
                if doc[field].endswith("Z"):
                    doc[field] = datetime.fromisoformat(
                        doc[field].replace("Z", "+00:00")
                    )
                else:
                    doc[field] = datetime.fromisoformat(doc[field])
            except ValueError:
                pass  # Keep as string if parsing fails

    return doc


class EvaluationRepository:
    def __init__(self, client: MongoDBClient) -> None:
        self._client = client

    async def _collection(self):
        return await self._client.collection("Evaluation")

    async def create_evaluation(self, payload: dict[str, Any]) -> EvaluationRecord:
        doc = _doc_from_payload(payload)
        collection = await self._collection()
        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _evaluation_from_doc(doc)

    async def update_evaluation(
        self, evaluation_id: str, payload: dict[str, Any]
    ) -> EvaluationRecord | None:
        try:
            doc = _doc_from_payload(payload)
            collection = await self._collection()

            # Remove _id if present in payload
            doc.pop("_id", None)

            result = await collection.update_one(
                {"_id": ObjectId(evaluation_id)},
                {"$set": doc},
            )

            if result.matched_count == 0:
                return None

            # Fetch updated document
            return await self.get_evaluation(evaluation_id)
        except Exception as exc:
            print(f"update_evaluation failed evaluation_id={evaluation_id} error={exc}")
            return None

    async def get_evaluation(self, evaluation_id: str) -> EvaluationRecord | None:
        try:
            collection = await self._collection()
            doc = await collection.find_one({"_id": ObjectId(evaluation_id)})
            if doc is None:
                return None
            return _evaluation_from_doc(doc)
        except Exception:
            return None

    async def get_by_session(self, session_id: str) -> EvaluationRecord | None:
        try:
            collection = await self._collection()
            # Query by sessionId field (string)
            doc = await collection.find_one({"sessionId": session_id})
            if doc is None:
                return None
            return _evaluation_from_doc(doc)
        except Exception:
            return None
