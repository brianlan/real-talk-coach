from __future__ import annotations

import httpx
import pytest
from fastapi import status

from app.api.routes import scenarios as scenarios_routes
from app.main import app
from app.repositories.scenario_repository import Scenario, Skill


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

    app.dependency_overrides[scenarios_routes._repo] = lambda: FakeRepo()
    yield
    app.dependency_overrides.pop(scenarios_routes._repo, None)


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
    payload = {
        "scenarioId": "scenario-1",
        "clientSessionStartedAt": "2025-01-01T00:00:00Z",
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
    payload = {
        "scenarioId": "scenario-1",
        "clientSessionStartedAt": "2025-01-01T00:00:00Z",
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
