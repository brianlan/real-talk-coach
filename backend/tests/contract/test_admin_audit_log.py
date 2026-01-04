from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from fastapi import status

from app.config import load_settings
from app.main import app
from app.repositories.audit_log_repository import AuditLogRecord


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
    calls: list[dict[str, str | None]] = []

    async def fake_list_audit_entries(**kwargs):
        calls.append(kwargs)
        return [
            AuditLogRecord(
                id="entry-1",
                admin_id="alice",
                action="create",
                entity_type="skill",
                entity_id="skill-1",
                timestamp="2025-01-01T00:00:00Z",
                details="Created skill",
            ),
            AuditLogRecord(
                id="entry-2",
                admin_id="bob",
                action="delete",
                entity_type="scenario",
                entity_id="scenario-9",
                timestamp="2025-01-02T00:00:00Z",
                details=None,
            ),
        ]

    monkeypatch.setattr(
        "app.api.routes.admin.audit_log.list_audit_entries",
        fake_list_audit_entries,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client, calls


def _admin_headers():
    token = load_settings().admin_access_token
    return {"X-Admin-Token": token}


@pytest.mark.asyncio
async def test_requires_admin_token(client):
    test_client, _ = client
    response = await test_client.get("/api/admin/audit-log")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_returns_entries_with_filters(client):
    test_client, calls = client
    headers = _admin_headers()
    response = await test_client.get(
        "/api/admin/audit-log?entityType=skill&adminId=alice&startDate=2025-01-01T00:00:00Z&endDate=2025-01-02T00:00:00Z",
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "entries" in body
    assert len(body["entries"]) == 2
    assert body["entries"][0]["entityId"] == "skill-1"
    assert calls[-1] == {
        "entity_type": "skill",
        "admin_id": "alice",
        "start_date": "2025-01-01T00:00:00Z",
        "end_date": "2025-01-02T00:00:00Z",
    }
