from __future__ import annotations

import httpx
import pytest
from fastapi import status

from datetime import datetime, timezone

from app.api.routes import scenarios as scenarios_routes
from app.api.routes import sessions as sessions_routes
from app.main import app
from app.repositories.scenario_repository import Scenario, Skill
from app.repositories.session_repository import PracticeSessionRecord


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("LEAN_APP_ID", "app")
    monkeypatch.setenv("LEAN_APP_KEY", "key")
    monkeypatch.setenv("LEAN_MASTER_KEY", "master")
    monkeypatch.setenv("LEAN_SERVER_URL", "https://api.leancloud.cn")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash")
    monkeypatch.setenv("CHATAI_API_BASE", "https://api.chataiapi.com/v1")
    monkeypatch.setenv("CHATAI_API_KEY", "secret")
    monkeypatch.setenv("CHATAI_API_MODEL", "gpt-5-mini")
    monkeypatch.setenv("EVALUATOR_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OBJECTIVE_CHECK_API_KEY", "secret")
    monkeypatch.setenv("OBJECTIVE_CHECK_MODEL", "gpt-5-mini")
    monkeypatch.setenv("STUB_USER_ID", "pilot-user")


@pytest.fixture(autouse=True)
def _override_repo():
    async def _list_published(*args, **kwargs):
        return [
            Scenario(
                id="scenario-1",
                category="Feedback",
                title="Sample",
                description="Desc",
                objective="Objective",
                ai_persona={"name": "AI", "role": "Coach", "background": ""},
                trainee_persona={"name": "You", "role": "Trainee", "background": ""},
                end_criteria=["End"],
                skills=["skill-1"],
                skill_summaries=[{"skillId": "skill-1", "name": "Skill", "rubric": "Rubric"}],
                idle_limit_seconds=8,
                duration_limit_seconds=300,
                prompt="Prompt",
                status="published",
            )
        ]

    async def _list_skills(*args, **kwargs):
        return [
            Skill(
                id="skill-1",
                external_id="skill_external",
                name="Skill",
                category="Category",
                rubric="Rubric",
                description=None,
            )
        ]

    async def _get(*args, **kwargs):
        return None

    class FakeRepo:
        list_published = staticmethod(_list_published)
        list_skills = staticmethod(_list_skills)
        get = staticmethod(_get)

    created_session: PracticeSessionRecord | None = None

    async def _list_sessions(stub_user_id=None):
        return []

    async def _create_session(payload):
        nonlocal created_session
        created_session = PracticeSessionRecord(
            id="session-1",
            scenario_id=payload["scenarioId"],
            stub_user_id=payload["stubUserId"],
            status=payload["status"],
            client_session_started_at=payload["clientSessionStartedAt"],
            started_at=payload["startedAt"],
            ended_at=payload["endedAt"],
            total_duration_seconds=payload["totalDurationSeconds"],
            idle_limit_seconds=payload["idleLimitSeconds"],
            duration_limit_seconds=payload["durationLimitSeconds"],
            ws_channel=payload["wsChannel"],
            objective_status=payload["objectiveStatus"],
            objective_reason=payload["objectiveReason"],
            termination_reason=payload["terminationReason"],
            evaluation_id=payload["evaluationId"],
        )
        return created_session

    async def _update_session(session_id, payload):
        nonlocal created_session
        if created_session is not None:
            return PracticeSessionRecord(
                id=session_id,
                scenario_id=created_session.scenario_id,
                stub_user_id=created_session.stub_user_id,
                status=payload.get("status", created_session.status),
                client_session_started_at=created_session.client_session_started_at,
                started_at=created_session.started_at,
                ended_at=payload.get("endedAt", created_session.ended_at),
                total_duration_seconds=created_session.total_duration_seconds,
                idle_limit_seconds=created_session.idle_limit_seconds,
                duration_limit_seconds=created_session.duration_limit_seconds,
                ws_channel=payload.get("wsChannel", created_session.ws_channel),
                objective_status=created_session.objective_status,
                objective_reason=created_session.objective_reason,
                termination_reason=payload.get(
                    "terminationReason", created_session.termination_reason
                ),
                evaluation_id=created_session.evaluation_id,
            )
        return PracticeSessionRecord(
            id=session_id,
            scenario_id="scenario-1",
            stub_user_id="pilot-user",
            status=payload.get("status", "pending"),
            client_session_started_at=payload.get("clientSessionStartedAt", ""),
            started_at=payload.get("startedAt"),
            ended_at=payload.get("endedAt"),
            total_duration_seconds=payload.get("totalDurationSeconds"),
            idle_limit_seconds=payload.get("idleLimitSeconds"),
            duration_limit_seconds=payload.get("durationLimitSeconds"),
            ws_channel=payload.get("wsChannel", "/ws/sessions/session-1"),
            objective_status=payload.get("objectiveStatus", "unknown"),
            objective_reason=payload.get("objectiveReason"),
            termination_reason=payload.get("terminationReason"),
            evaluation_id=payload.get("evaluationId"),
        )

    async def _add_turn(payload):
        return type(
            "Turn",
            (),
            {
                "id": "turn-0",
                "session_id": payload["sessionId"],
                "sequence": payload["sequence"],
                "speaker": payload["speaker"],
                "transcript": payload["transcript"],
                "audio_file_id": payload["audioFileId"],
                "audio_url": payload["audioUrl"],
                "asr_status": payload["asrStatus"],
                "created_at": payload.get("createdAt"),
                "started_at": payload["startedAt"],
                "ended_at": payload["endedAt"],
                "context": payload.get("context"),
                "latency_ms": payload.get("latencyMs"),
            },
        )()

    class FakeSessionRepo:
        list_sessions = staticmethod(_list_sessions)
        create_session = staticmethod(_create_session)
        update_session = staticmethod(_update_session)
        add_turn = staticmethod(_add_turn)

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return type(
                "Scenario",
                (),
                {
                    "prompt": "Hello",
                    "status": "published",
                    "idle_limit_seconds": 8,
                    "duration_limit_seconds": 300,
                },
            )()

    app.dependency_overrides[scenarios_routes._repo] = lambda: FakeRepo()
    app.dependency_overrides[sessions_routes._repo] = lambda: FakeSessionRepo()
    app.dependency_overrides[sessions_routes._scenario_repo] = lambda: FakeScenarioRepo()
    yield
    app.dependency_overrides.pop(scenarios_routes._repo, None)
    app.dependency_overrides.pop(sessions_routes._repo, None)
    app.dependency_overrides.pop(sessions_routes._scenario_repo, None)


@pytest.mark.asyncio
async def test_create_session_missing_timestamps_rejected():
    payload = {"scenarioId": "scenario-1"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_list_scenarios_contract():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/scenarios", params={"historyStepCount": 1})

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert "items" in payload


@pytest.mark.asyncio
async def test_list_skills_contract():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/skills")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert "items" in payload


@pytest.mark.asyncio
async def test_create_session_contract():
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "scenarioId": "scenario-1",
        "clientSessionStartedAt": now,
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["scenarioId"] == payload["scenarioId"]
    assert body["clientSessionStartedAt"] == payload["clientSessionStartedAt"]
    assert "id" in body
    assert "wsChannel" in body


@pytest.mark.asyncio
async def test_create_session_rejects_incomplete_scenario():
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "scenarioId": "scenario-1",
        "clientSessionStartedAt": now,
        "personas": {},
        "objectives": [],
        "endCriteria": [],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body = response.json()
    assert "error" in body or "detail" in body
