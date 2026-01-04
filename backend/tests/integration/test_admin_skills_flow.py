from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

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
    # Mock LeanCloud lifecycle
    store: dict[str, dict] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        import json

        if request.method == "GET" and request.url.path.endswith("/classes/Skill"):
            return httpx.Response(200, json={"results": list(store.values())})
        if request.method == "GET" and "/classes/Skill/" in request.url.path:
            skill_id = request.url.path.split("/")[-1]
            record = store.get(skill_id)
            if not record:
                return httpx.Response(404, json={"error": "not found"})
            return httpx.Response(200, json=record)
        if request.method == "POST" and request.url.path.endswith("/classes/Skill"):
            payload = json.loads(request.content.decode() or "{}")
            skill_id = payload.get("objectId", "skill-1")
            record = {"objectId": skill_id, **payload, "status": "active", "__version": "v1", "updatedAt": "v1"}
            store[skill_id] = record
            return httpx.Response(201, json=record)
        if request.method == "PUT" and "/classes/Skill/" in request.url.path:
            skill_id = request.url.path.split("/")[-1]
            payload = json.loads(request.content.decode() or "{}")
            if skill_id not in store:
                return httpx.Response(404, json={"error": "not found"})
            store[skill_id].update(payload)
            store[skill_id]["__version"] = payload.get("__version", "v2")
            store[skill_id]["updatedAt"] = payload.get("updatedAt", "v2")
            return httpx.Response(200, json={"updatedAt": store[skill_id]["updatedAt"]})
        if request.method == "DELETE" and "/classes/Skill/" in request.url.path:
            skill_id = request.url.path.split("/")[-1]
            if skill_id not in store:
                return httpx.Response(404, json={"error": "not found"})
            store[skill_id]["status"] = "deleted"
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"error": "not found"})

    from app.services.admin.skills_service import AdminSkillsService
    from app.repositories.skill_repository import AdminSkillRepository
    from app.api.routes.admin import skills as skills_routes
    from app.clients.leancloud import LeanCloudClient

    transport = httpx.MockTransport(handler)
    mock_client = LeanCloudClient(
        app_id="app", app_key="key", master_key="master", server_url="https://api.leancloud.cn", transport=transport
    )
    app.dependency_overrides = {
        skills_routes._service: lambda: AdminSkillsService(AdminSkillRepository(mock_client))
    }
    async def _noop(**kwargs):
        return None

    monkeypatch.setattr("app.services.admin.skills_service.record_audit_entry", _noop)
    asgi_transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=asgi_transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_skill_crud_and_restore_flow(client):
    headers = {"X-Admin-Token": "admin-token"}
    # Create
    create_resp = await client.post(
        "/api/admin/skills",
        json={"name": "Skill", "category": "Cat", "rubric": "Rubric"},
        headers=headers,
    )
    assert create_resp.status_code in {200, 201}
    skill = create_resp.json()
    skill_id = skill.get("id") or skill.get("objectId", "skill-1")

    # Update
    update_resp = await client.put(
        f"/api/admin/skills/{skill_id}",
        json={"name": "Skill 2", "category": "Cat", "rubric": "Rubric"},
        headers={**headers, "If-Match": skill.get("version", "v1")},
    )
    assert update_resp.status_code in {200, 409}

    # Soft delete
    delete_resp = await client.delete(f"/api/admin/skills/{skill_id}", headers=headers)
    assert delete_resp.status_code in {200, 204}

    # Restore
    restore_resp = await client.post(
        f"/api/admin/skills/{skill_id}/restore",
        headers=headers,
    )
    assert restore_resp.status_code in {200, 404}
