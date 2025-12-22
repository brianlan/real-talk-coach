from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.clients.leancloud import LeanCloudClient
from app.config import load_settings
from app.models.session import PracticeSessionCreate
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.session_repository import PracticeSessionRecord, SessionRepository

router = APIRouter()


def _repo() -> SessionRepository:
    settings = load_settings()
    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    return SessionRepository(client)


def _scenario_repo() -> ScenarioRepository:
    settings = load_settings()
    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    return ScenarioRepository(client)


def _session_response(session: PracticeSessionRecord) -> dict[str, Any]:
    return {
        "id": session.id,
        "scenarioId": session.scenario_id,
        "stubUserId": session.stub_user_id,
        "status": session.status,
        "terminationReason": session.termination_reason,
        "clientSessionStartedAt": session.client_session_started_at,
        "startedAt": session.started_at,
        "endedAt": session.ended_at,
        "totalDurationSeconds": session.total_duration_seconds,
        "idleLimitSeconds": session.idle_limit_seconds,
        "durationLimitSeconds": session.duration_limit_seconds,
        "wsChannel": session.ws_channel,
        "objectiveStatus": session.objective_status,
        "objectiveReason": session.objective_reason,
        "evaluationId": session.evaluation_id,
    }


def _scenario_response(scenario) -> dict[str, Any]:
    return {
        "id": scenario.id,
        "category": scenario.category,
        "title": scenario.title,
        "description": scenario.description,
        "objective": scenario.objective,
        "aiPersona": scenario.ai_persona,
        "traineePersona": scenario.trainee_persona,
        "endCriteria": scenario.end_criteria,
        "skills": scenario.skills,
        "skillSummaries": scenario.skill_summaries,
        "idleLimitSeconds": scenario.idle_limit_seconds,
        "durationLimitSeconds": scenario.duration_limit_seconds,
        "prompt": scenario.prompt,
    }


def _turn_response(turn) -> dict[str, Any]:
    return {
        "id": turn.id,
        "sessionId": turn.session_id,
        "sequence": turn.sequence,
        "speaker": turn.speaker,
        "transcript": turn.transcript,
        "audioFileId": turn.audio_file_id,
        "audioUrl": turn.audio_url,
        "asrStatus": turn.asr_status,
        "createdAt": turn.created_at,
        "startedAt": turn.started_at,
        "endedAt": turn.ended_at,
        "context": turn.context,
        "latencyMs": turn.latency_ms,
    }


@router.get("/sessions")
async def list_sessions(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, le=50),
    scenarioId: str | None = None,
    category: str | None = None,
    search: str | None = None,
    sort: str = Query("startedAtDesc"),
):
    return {
        "items": [],
        "page": page,
        "pageSize": pageSize,
        "total": 0,
    }


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: PracticeSessionCreate,
    repo: SessionRepository = Depends(_repo),
):
    settings = load_settings()
    now = datetime.now(timezone.utc).isoformat()
    record = await repo.create_session(
        {
            "scenarioId": payload.scenarioId,
            "stubUserId": settings.stub_user_id,
            "status": "pending",
            "clientSessionStartedAt": payload.clientSessionStartedAt.isoformat(),
            "startedAt": now,
            "endedAt": None,
            "totalDurationSeconds": None,
            "idleLimitSeconds": None,
            "durationLimitSeconds": None,
            "wsChannel": "/ws/sessions/pending",
            "objectiveStatus": "unknown",
            "objectiveReason": None,
            "terminationReason": None,
            "evaluationId": None,
        }
    )

    if record.ws_channel.endswith("/pending"):
        record = await repo.update_session(
            record.id,
            {"wsChannel": f"/ws/sessions/{record.id}"},
        ) or record

    return _session_response(record)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    historyStepCount: int = Query(..., ge=1),
    repo: SessionRepository = Depends(_repo),
    scenario_repo: ScenarioRepository = Depends(_scenario_repo),
):
    session = await repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    turns = await repo.list_turns(session_id)
    scenario = await scenario_repo.get(session.scenario_id)
    return {
        "session": _session_response(session),
        "scenario": _scenario_response(scenario) if scenario else None,
        "turns": [_turn_response(turn) for turn in turns],
        "evaluation": None,
    }


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    return None


@router.post("/sessions/{session_id}/manual-stop", status_code=status.HTTP_202_ACCEPTED)
async def manual_stop(
    session_id: str,
    payload: dict[str, Any],
    repo: SessionRepository = Depends(_repo),
):
    reason = payload.get("reason")
    if reason not in {"manual", "qa_error", "media_error"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    record = await repo.update_session(
        session_id,
        {
            "status": "ended",
            "terminationReason": reason,
            "endedAt": datetime.now(timezone.utc).isoformat(),
        },
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"status": "acknowledged"}
