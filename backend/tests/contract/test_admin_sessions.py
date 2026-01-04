from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from fastapi import status

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
    from app.api.routes.admin import sessions as sessions_routes
    from app.services.admin.sessions_service import AdminSessionsService
    from app.repositories.session_repository import SessionRepository
    from app.clients.leancloud import LeanCloudClient

    sessions_store: list[dict] = [
        {
            "objectId": "session-1",
            "scenarioId": "scenario-1",
            "status": "ended",
            "startedAt": "2025-01-01T00:00:00Z",
            "endedAt": "2025-01-01T00:10:00Z",
            "terminationReason": "manual",
            "evaluationStatus": "completed",
            "transcript": [],
        }
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path.endswith("/classes/PracticeSession"):
            return httpx.Response(200, json={"results": sessions_store})
        if request.method == "GET" and "/classes/PracticeSession/" in path:
            sid = path.split("/")[-1]
            match = next((s for s in sessions_store if s["objectId"] == sid), None)
            if not match:
                return httpx.Response(404, json={"error": "not found"})
            return httpx.Response(200, json=match)
        if request.method == "DELETE" and "/classes/PracticeSession/" in path:
            sid = path.split("/")[-1]
            if sid not in [s["objectId"] for s in sessions_store]:
                return httpx.Response(404, json={"error": "not found"})
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
    monkeypatch.setattr("app.services.admin.sessions_service.record_audit_entry", _noop)
    app.dependency_overrides = {
        sessions_routes._service: lambda: AdminSessionsService(SessionRepository(mock_client))
    }
    asgi_transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=asgi_transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides = {}


def _admin_headers():
    return {"X-Admin-Token": "admin-token"}


@pytest.mark.asyncio
async def test_list_sessions_requires_admin(client):
    res = await client.get("/api/admin/sessions")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_list_sessions_success(client):
    res = await client.get("/api/admin/sessions", headers=_admin_headers())
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    assert "sessions" in body


@pytest.mark.asyncio
async def test_delete_session(client):
    res = await client.delete("/api/admin/sessions/session-1", headers=_admin_headers())
    assert res.status_code in {status.HTTP_204_NO_CONTENT, status.HTTP_200_OK}
