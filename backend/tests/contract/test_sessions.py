from __future__ import annotations

import httpx
import pytest
from fastapi import status

from app.main import app


@pytest.mark.asyncio
async def test_list_scenarios_contract():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/scenarios", params={"historyStepCount": 1})

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert "items" in payload


@pytest.mark.asyncio
async def test_list_skills_contract():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
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

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
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

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/sessions", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body = response.json()
    assert "error" in body or "detail" in body
