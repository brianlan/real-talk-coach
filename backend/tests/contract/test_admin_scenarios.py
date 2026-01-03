from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from fastapi import status, HTTPException

from app.main import app


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
    monkeypatch.setenv("ADMIN_ACCESS_TOKEN", "admin-token")


@pytest_asyncio.fixture
async def client(monkeypatch):
    from app.api.routes.admin import scenarios as scenarios_routes
    from app.repositories.admin_scenario_repository import AdminScenarioRepository
    from app.services.admin.scenarios_service import AdminScenariosService
    from app.clients.leancloud import LeanCloudClient

    store: dict[str, dict] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        import json

        path = request.url.path
        if request.method == "GET" and path.endswith("/classes/Skill"):
            return httpx.Response(200, json={"results": []})
        if request.method == "GET" and path.endswith("/classes/Scenario"):
            return httpx.Response(200, json={"results": list(store.values())})
        if request.method == "GET" and "/classes/Scenario/" in path:
            sid = path.split("/")[-1]
            record = store.get(sid)
            if not record:
                return httpx.Response(404, json={"error": "not found"})
            return httpx.Response(200, json=record)
        if request.method == "POST" and path.endswith("/classes/Scenario"):
            payload = json.loads(request.content.decode() or "{}")
            sid = payload.get("objectId", "scenario-1")
            record = {"objectId": sid, **payload, "status": payload.get("status", "draft"), "updatedAt": "v1"}
            store[sid] = record
            return httpx.Response(201, json=record)
        if request.method == "PUT" and "/classes/Scenario/" in path:
            sid = path.split("/")[-1]
            if sid not in store:
                return httpx.Response(404, json={"error": "not found"})
            payload = json.loads(request.content.decode() or "{}")
            store[sid].update(payload)
            store[sid]["updatedAt"] = payload.get("updatedAt", "v2")
            return httpx.Response(200, json={"updatedAt": store[sid]["updatedAt"]})
        if request.method == "DELETE" and "/classes/Scenario/" in path:
            sid = path.split("/")[-1]
            if sid not in store:
                return httpx.Response(404, json={"error": "not found"})
            store[sid]["status"] = "deleted"
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    mock_client = LeanCloudClient(
        app_id="app",
        app_key="key",
        master_key="master",
        server_url="https://api.leancloud.cn",
        transport=transport,
    )
    async def _noop(**kwargs):
        return None
    monkeypatch.setattr("app.services.admin.scenarios_service.record_audit_entry", _noop)
    app.dependency_overrides = {
        scenarios_routes._service: lambda: AdminScenariosService(AdminScenarioRepository(mock_client))
    }
    asgi_transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=asgi_transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides = {}


def _admin_headers():
    return {"X-Admin-Token": "admin-token"}


def _sample_payload():
    return {
        "category": "Feedback",
        "title": "Scenario",
        "description": "Desc",
        "objective": "Objective",
        "aiPersona": {"name": "AI", "role": "Coach", "background": ""},
        "traineePersona": {"name": "You", "role": "Trainee", "background": ""},
        "endCriteria": ["End"],
        "skills": ["skill-1"],
        "prompt": "Prompt",
        "status": "draft",
    }


@pytest.mark.asyncio
async def test_create_scenario_requires_admin_token(client):
    res = await client.post("/api/admin/scenarios", json=_sample_payload())
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_scenario_succeeds(client):
    res = await client.post("/api/admin/scenarios", json=_sample_payload(), headers=_admin_headers())
    assert res.status_code in {status.HTTP_200_OK, status.HTTP_201_CREATED}
    body = res.json()
    assert body.get("title") == "Scenario"


@pytest.mark.asyncio
async def test_publish_requires_complete_fields(client):
    payload = _sample_payload()
    payload["skills"] = []
    res = await client.post("/api/admin/scenarios", json=payload, headers=_admin_headers())
    assert res.status_code in {status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY}


@pytest.mark.asyncio
async def test_delete_blocked_when_sessions_exist(client, monkeypatch):
    # Simulate sessions by forcing service to raise conflict
    monkeypatch.setattr(
        "app.services.admin.scenarios_service.AdminScenariosService.soft_delete_scenario",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scenario has sessions")
        ),
    )
    res = await client.delete("/api/admin/scenarios/scenario-1", headers=_admin_headers())
    assert res.status_code in {status.HTTP_409_CONFLICT, status.HTTP_400_BAD_REQUEST}
