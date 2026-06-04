from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from bson.objectid import ObjectId

from app.clients.mongodb import MongoDBClient


@dataclass(frozen=True)
class PracticeSessionRecord:
    id: str
    scenario_id: str
    stub_user_id: str
    language: str | None
    opening_prompt: str | None
    status: str
    client_session_started_at: str
    started_at: str | None
    ended_at: str | None
    total_duration_seconds: int | None
    idle_limit_seconds: int | None
    duration_limit_seconds: int | None
    ws_channel: str
    objective_status: str
    objective_reason: str | None
    termination_reason: str | None
    evaluation_id: str | None
    user_id: str | None = None
    mode: Literal["turn_based", "realtime"] = "turn_based"
    rtc_room_id: Optional[str] = None
    rtc_task_id: Optional[str] = None
    realtime_state: Optional[Literal["connecting", "active", "ended"]] = None


@dataclass(frozen=True)
class TurnRecord:
    id: str
    session_id: str
    sequence: int
    speaker: str
    transcript: str | None
    audio_file_id: str
    audio_url: str | None
    asr_status: str | None
    created_at: str | None
    started_at: str | None
    ended_at: str | None
    context: str | None
    latency_ms: int | None
    is_interrupted: bool = False
    interrupted_at_ms: Optional[int] = None


def _normalize_termination_reason(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("reason") or raw.get("value")
    if isinstance(raw, str):
        return raw
    return None


def _normalize_evaluation_id(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("id") or raw.get("objectId")
    if isinstance(raw, str):
        return raw
    return None


def _normalize_opening_prompt(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return raw.get("text") or raw.get("prompt")
    if isinstance(raw, str):
        return raw
    return None


def _normalize_date(raw: Any) -> str | None:
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(raw, str):
        return raw
    return None


def _session_from_doc(doc: dict[str, Any]) -> PracticeSessionRecord:
    return PracticeSessionRecord(
        id=str(doc.get("_id", "")),
        scenario_id=doc.get("scenarioId", ""),
        stub_user_id=doc.get("stubUserId", ""),
        user_id=doc.get("userId"),
        language=doc.get("language"),
        opening_prompt=_normalize_opening_prompt(doc.get("openingPrompt")),
        status=doc.get("status", "pending"),
        client_session_started_at=_normalize_date(doc.get("clientSessionStartedAt"))
        or "",
        started_at=_normalize_date(doc.get("startedAt")),
        ended_at=_normalize_date(doc.get("endedAt")),
        total_duration_seconds=doc.get("totalDurationSeconds"),
        idle_limit_seconds=doc.get("idleLimitSeconds"),
        duration_limit_seconds=doc.get("durationLimitSeconds"),
        ws_channel=doc.get("wsChannel", ""),
        objective_status=doc.get("objectiveStatus", "unknown"),
        objective_reason=doc.get("objectiveReason"),
        termination_reason=_normalize_termination_reason(doc.get("terminationReason")),
        evaluation_id=_normalize_evaluation_id(doc.get("evaluationId")),
        mode=doc.get("mode", "turn_based"),
        rtc_room_id=doc.get("rtcRoomId"),
        rtc_task_id=doc.get("rtcTaskId"),
        realtime_state=doc.get("realtimeState"),
    )


def _turn_from_doc(doc: dict[str, Any]) -> TurnRecord:
    return TurnRecord(
        id=str(doc.get("_id", "")),
        session_id=doc.get("sessionId", ""),
        sequence=doc.get("sequence", 0),
        speaker=doc.get("speaker", ""),
        transcript=doc.get("transcript"),
        audio_file_id=doc.get("audioFileId", ""),
        audio_url=doc.get("audioUrl"),
        asr_status=doc.get("asrStatus"),
        created_at=_normalize_date(doc.get("createdAt")),
        started_at=_normalize_date(doc.get("startedAt")),
        ended_at=_normalize_date(doc.get("endedAt")),
        context=doc.get("context"),
        latency_ms=doc.get("latencyMs"),
        is_interrupted=doc.get("isInterrupted", False),
        interrupted_at_ms=doc.get("interruptedAtMs"),
    )


def _doc_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert payload to MongoDB document, handling special fields."""
    doc = dict(payload)

    # Handle date fields - store as datetime objects
    date_fields = ["clientSessionStartedAt", "startedAt", "endedAt", "createdAt"]
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


class SessionRepository:
    def __init__(self, client: MongoDBClient) -> None:
        self._client = client

    async def _sessions_collection(self):
        return await self._client.collection("PracticeSession")

    async def _turns_collection(self):
        return await self._client.collection("Turn")

    async def create_session(self, payload: dict[str, Any]) -> PracticeSessionRecord:
        doc = _doc_from_payload(payload)
        collection = await self._sessions_collection()
        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _session_from_doc(doc)

    async def get_session(self, session_id: str) -> PracticeSessionRecord | None:
        try:
            collection = await self._sessions_collection()
            doc = await collection.find_one({"_id": ObjectId(session_id)})
            if doc is None:
                return None
            return _session_from_doc(doc)
        except Exception:
            return None

    async def get_session_by_rtc_task_id(self, rtc_task_id: str) -> PracticeSessionRecord | None:
        if not rtc_task_id:
            return None
        try:
            collection = await self._sessions_collection()
            doc = await collection.find_one(
                {"rtcTaskId": rtc_task_id},
                sort=[("startedAt", -1)],
            )
            if doc is None:
                return None
            return _session_from_doc(doc)
        except Exception:
            return None

    async def get_session_by_rtc_room_id(self, rtc_room_id: str) -> PracticeSessionRecord | None:
        if not rtc_room_id:
            return None
        try:
            collection = await self._sessions_collection()
            doc = await collection.find_one(
                {"rtcRoomId": rtc_room_id},
                sort=[("startedAt", -1)],
            )
            if doc is None:
                return None
            return _session_from_doc(doc)
        except Exception:
            return None

    async def update_session(
        self, session_id: str, payload: dict[str, Any]
    ) -> PracticeSessionRecord | None:
        try:
            doc = _doc_from_payload(payload)
            collection = await self._sessions_collection()

            # Remove _id if present in payload
            doc.pop("_id", None)

            result = await collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": doc},
            )

            if result.matched_count == 0:
                return None

            # Fetch updated document
            return await self.get_session(session_id)
        except Exception as exc:
            print(f"update_session failed session_id={session_id} error={exc}")
            return None

    async def add_turn(self, payload: dict[str, Any]) -> TurnRecord:
        defaults = {
            "audioUrl": "",
            "asrStatus": "not_applicable",
            "context": "",
            "latencyMs": -1,
        }
        normalized = {**defaults, **payload}
        for key, default in defaults.items():
            if normalized.get(key) is None:
                normalized[key] = default

        doc = _doc_from_payload(normalized)
        collection = await self._turns_collection()
        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _turn_from_doc(doc)

    async def update_turn(self, turn_id: str, payload: dict[str, Any]) -> TurnRecord | None:
        try:
            doc = _doc_from_payload(payload)
            collection = await self._turns_collection()

            # Remove _id if present in payload
            doc.pop("_id", None)

            result = await collection.update_one(
                {"_id": ObjectId(turn_id)},
                {"$set": doc},
            )

            if result.matched_count == 0:
                return None

            # Fetch and return updated turn
            return await self.get_turn(turn_id)
        except Exception:
            return None

    async def list_turns(self, session_id: str) -> list[TurnRecord]:
        collection = await self._turns_collection()
        cursor = collection.find({"sessionId": session_id})
        docs = await cursor.to_list(length=1000)
        return [_turn_from_doc(doc) for doc in docs]

    async def get_turn(self, turn_id: str) -> TurnRecord | None:
        try:
            collection = await self._turns_collection()
            doc = await collection.find_one({"_id": ObjectId(turn_id)})
            if doc is None:
                return None
            return _turn_from_doc(doc)
        except Exception:
            return None

    async def list_sessions(
        self,
        stub_user_id: str | None = None,
        user_id: str | None = None,
    ) -> list[PracticeSessionRecord]:
        query = {}
        if stub_user_id:
            query["stubUserId"] = stub_user_id
        if user_id:
            query["userId"] = user_id

        try:
            collection = await self._sessions_collection()
            cursor = collection.find(query)
            docs = await cursor.to_list(length=1000)
            return [_session_from_doc(doc) for doc in docs]
        except Exception:
            return []

    async def delete_session(self, session_id: str) -> None:
        collection = await self._sessions_collection()
        await collection.delete_one({"_id": ObjectId(session_id)})
