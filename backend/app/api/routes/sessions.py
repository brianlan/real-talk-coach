from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.clients.leancloud import LeanCloudClient
from app.config import load_settings
from app.models.session import PracticeSessionCreate, enforce_drift
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.session_repository import PracticeSessionRecord, SessionRepository
from app.services.session_service import (
    CapacityError,
    ensure_capacity,
    initiate_session,
    terminate_session,
)
from app.services.session_cleanup import cleanup_session
from app.telemetry.tracing import emit_event
from app.telemetry.otel import start_span

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
        "language": session.language,
        "openingPrompt": session.opening_prompt,
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




def _validate_scenario_for_practice(scenario) -> None:
    missing: list[str] = []

    ai_persona = getattr(scenario, "ai_persona", None)
    trainee_persona = getattr(scenario, "trainee_persona", None)
    objective = getattr(scenario, "objective", "") or ""
    end_criteria = getattr(scenario, "end_criteria", None) or []

    if not ai_persona:
        missing.append("aiPersona")
    else:
        if not ai_persona.get("name"):
            missing.append("aiPersona.name")
        if not ai_persona.get("background"):
            missing.append("aiPersona.background")

    if not trainee_persona:
        missing.append("traineePersona")
    else:
        if not trainee_persona.get("name"):
            missing.append("traineePersona.name")
        if not trainee_persona.get("background"):
            missing.append("traineePersona.background")

    if not objective:
        missing.append("objective")
    if not end_criteria:
        missing.append("endCriteria")

    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Scenario missing required fields: " + ", ".join(sorted(missing)),
        )


def _detect_language(scenario) -> str:
    text_bits = [
        getattr(scenario, "title", "") or "",
        getattr(scenario, "description", "") or "",
        getattr(scenario, "objective", "") or "",
    ]
    text = " ".join(bit for bit in text_bits if bit)
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    return "en"


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: PracticeSessionCreate,
    background_tasks: BackgroundTasks,
    repo: SessionRepository = Depends(_repo),
    scenario_repo: ScenarioRepository = Depends(_scenario_repo),
):
    with start_span(
        "sessions.create",
        {"scenarioId": payload.scenarioId},
    ):
        settings = load_settings()
        scenario = await scenario_repo.get(payload.scenarioId)
        if not scenario or scenario.status != "published":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Scenario is not available for practice.",
            )
        _validate_scenario_for_practice(scenario)
        language = payload.language or _detect_language(scenario)
        try:
            enforce_drift(payload.clientSessionStartedAt, datetime.now(timezone.utc))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        try:
            await ensure_capacity(repo, max_active=20)
        except CapacityError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
            ) from exc
        now = datetime.now(timezone.utc).isoformat()
        record = await repo.create_session(
            {
                "scenarioId": payload.scenarioId,
                "stubUserId": settings.stub_user_id,
                "language": language,
                "openingPrompt": None,
                "status": "pending",
                "clientSessionStartedAt": payload.clientSessionStartedAt.isoformat(),
                "startedAt": now,
                "endedAt": None,
                "totalDurationSeconds": None,
                "idleLimitSeconds": scenario.idle_limit_seconds,
                "durationLimitSeconds": scenario.duration_limit_seconds,
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
    emit_event("session.created", session_id=record.id)
    background_tasks.add_task(
        initiate_session, repo, record.id, scenario=scenario, language=language
    )

    return _session_response(record)


@router.post("/sessions/{session_id}/practice-again", status_code=status.HTTP_201_CREATED)
async def practice_again(
    session_id: str,
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    repo: SessionRepository = Depends(_repo),
    scenario_repo: ScenarioRepository = Depends(_scenario_repo),
):
    with start_span("sessions.practice_again", {"sessionId": session_id}):
        session = await repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        settings = load_settings()
        if session.stub_user_id != settings.stub_user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        client_started = payload.get("clientSessionStartedAt")
        if not client_started:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
        new_payload = PracticeSessionCreate(
            scenarioId=session.scenario_id,
            clientSessionStartedAt=client_started,
            language=session.language,
        )
        return await create_session(
            new_payload,
            background_tasks=background_tasks,
            repo=repo,
            scenario_repo=scenario_repo,
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, repo: SessionRepository = Depends(_repo)):
    session = await repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await cleanup_session(session_id)
    return None


@router.post("/sessions/{session_id}/manual-stop", status_code=status.HTTP_202_ACCEPTED)
async def manual_stop(
    session_id: str,
    payload: dict[str, Any],
    repo: SessionRepository = Depends(_repo),
):
    with start_span("sessions.manual_stop", {"sessionId": session_id}):
        reason = payload.get("reason")
        if reason not in {"manual", "qa_error", "media_error"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    ended_at = datetime.now(timezone.utc).isoformat()
    update_payload = {
        "status": "ended",
        "terminationReason": reason,
        "endedAt": ended_at,
    }
    record = await repo.update_session(session_id, update_payload)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await terminate_session(repo, session_id, reason, ended_at)
    emit_event(
        "session.terminated",
        session_id=session_id,
        attributes={"reason": reason},
    )
    return {"status": "acknowledged"}
