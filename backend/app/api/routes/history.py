from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.clients.leancloud import LeanCloudClient
from app.config import load_settings
from app.repositories.evaluation_repository import EvaluationRecord, EvaluationRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.session_repository import PracticeSessionRecord, SessionRepository, TurnRecord
from app.telemetry.otel import start_span
from app.telemetry.tracing import emit_metric

router = APIRouter()


def _session_repo() -> SessionRepository:
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


def _evaluation_repo() -> EvaluationRepository:
    settings = load_settings()
    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    return EvaluationRepository(client)


def _signing_client() -> LeanCloudClient:
    settings = load_settings()
    return LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )


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


def _turn_response(turn: TurnRecord, signed_url: str | None) -> dict[str, Any]:
    return {
        "id": turn.id,
        "sessionId": turn.session_id,
        "sequence": turn.sequence,
        "speaker": turn.speaker,
        "transcript": turn.transcript,
        "audioFileId": turn.audio_file_id,
        "audioUrl": signed_url,
        "asrStatus": turn.asr_status,
        "createdAt": turn.created_at,
        "startedAt": turn.started_at,
        "endedAt": turn.ended_at,
        "context": turn.context,
        "latencyMs": turn.latency_ms,
    }


def _evaluation_response(record: EvaluationRecord) -> dict[str, Any]:
    return {
        "sessionId": record.session_id,
        "status": record.status,
        "scores": record.scores,
        "summary": record.summary,
        "evaluatorModel": record.evaluator_model,
        "attempts": record.attempts,
        "lastError": record.last_error,
        "queuedAt": record.queued_at,
        "completedAt": record.completed_at,
    }


def _emit_step_metric(session_id: str | None, step_count: int, *, scope: str) -> None:
    emit_metric(
        "history.step_count",
        float(step_count),
        session_id=session_id,
        attributes={"scope": scope},
    )


@router.get("/sessions")
async def list_history(
    historyStepCount: int = Query(..., ge=1),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, le=50),
    scenarioId: str | None = None,
    category: str | None = None,
    search: str | None = None,
    sort: str = Query("startedAtDesc"),
    repo: SessionRepository = Depends(_session_repo),
    scenario_repo: ScenarioRepository = Depends(_scenario_repo),
):
    with start_span(
        "history.list",
        {
            "historyPage": page,
            "pageSize": pageSize,
            "sort": sort,
            "category": category,
            "search": search,
            "scenarioId": scenarioId,
        },
    ):
        sessions = await repo.list_sessions(load_settings().stub_user_id)
        items = [
            session
            for session in sessions
            if (not scenarioId or session.scenario_id == scenarioId)
        ]
        if category or search:
            scenario_map: dict[str, Any] = {}
            for session in items:
                if session.scenario_id not in scenario_map:
                    with start_span(
                        "history.scenario_lookup",
                        {"scenarioId": session.scenario_id},
                    ):
                        scenario_map[session.scenario_id] = await scenario_repo.get(
                            session.scenario_id
                        )
            filtered: list[PracticeSessionRecord] = []
            for session in items:
                scenario = scenario_map.get(session.scenario_id)
                if not scenario:
                    continue
                if category and scenario.category != category:
                    continue
                if search:
                    haystack = f"{scenario.title} {scenario.objective}".lower()
                    if search.lower() not in haystack:
                        continue
                filtered.append(session)
            items = filtered
        if sort == "startedAtAsc":
            items.sort(key=lambda item: item.started_at or "")
        else:
            items.sort(key=lambda item: item.started_at or "", reverse=True)
        start = (page - 1) * pageSize
        end = start + pageSize
        paged = items[start:end]
        _emit_step_metric(None, historyStepCount, scope="list")
        return {
            "items": [_session_response(item) for item in paged],
            "page": page,
            "pageSize": pageSize,
            "total": len(items),
        }


@router.get("/sessions/{session_id}")
async def get_history_detail(
    session_id: str,
    historyStepCount: int = Query(..., ge=1),
    repo: SessionRepository = Depends(_session_repo),
    scenario_repo: ScenarioRepository = Depends(_scenario_repo),
    evaluation_repo: EvaluationRepository = Depends(_evaluation_repo),
    signing_client: LeanCloudClient = Depends(_signing_client),
):
    with start_span(
        "history.detail",
        {"sessionId": session_id, "historyStepCount": historyStepCount},
    ):
        session = await repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        settings = load_settings()
        if session.stub_user_id != settings.stub_user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        turns = await repo.list_turns(session_id)
        turns.sort(key=lambda turn: turn.sequence)
        scenario = await scenario_repo.get(session.scenario_id)
        evaluation = await evaluation_repo.get_by_session(session_id)
        urls = [turn.audio_url for turn in turns if turn.audio_url]
        signed_map = {}
        if urls:
            with start_span(
                "history.sign_urls",
                {"sessionId": session_id, "urlCount": len(urls)},
            ):
                signed_map = await signing_client.create_signed_urls(
                    urls, ttl_seconds=900
                )
        _emit_step_metric(session_id, historyStepCount, scope="detail")
        return {
            "session": _session_response(session),
            "scenario": _scenario_response(scenario) if scenario else None,
            "turns": [
                _turn_response(turn, signed_map.get(turn.audio_url))
                for turn in turns
            ],
            "evaluation": _evaluation_response(evaluation) if evaluation else None,
        }
