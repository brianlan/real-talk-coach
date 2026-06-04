"""Red-phase contract tests for admin scenario CRUD with the new nested schema.

These tests encode the canonical nested scenario shape for admin
create/update/publish operations.  They are expected to FAIL until
the production code is refactored.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import status

from app.api.routes.admin import scenarios as admin_scenarios_routes
from app.main import app


CANONICAL_NESTED_PAYLOAD = {
    "metadata": {
        "title": "Request a Salary Increase After Taking on Expanded Responsibilities",
        "slug": "salary-raise-expanded-responsibilities",
        "domain": "Workplace",
        "scenarioType": "Negotiation",
        "difficulty": "Medium",
        "conflictLevel": "Medium",
        "estimatedDurationMinutes": 8,
        "tags": ["salary negotiation", "career growth"],
    },
    "context": {
        "situation": (
            "An employee has taken on significant additional responsibilities "
            "after a teammate left the team."
        ),
        "background": (
            "The company is currently facing moderate budget pressure."
        ),
        "setting": "A scheduled one-on-one meeting between the employee and their manager.",
    },
    "simulationConfig": {
        "ai": {
            "name": "Jordan",
            "role": "Engineering Manager",
            "personality": ["professional", "pragmatic", "supportive but cautious"],
            "motivations": [
                "retain high-performing employees",
                "maintain fairness across the team",
            ],
            "constraints": [
                "raises above about 5-8% usually require director approval",
            ],
            "tendencies": [
                "initially cautious when employees request raises",
            ],
            "knowledge": [
                "the employee has taken on additional work after a teammate left",
            ],
            "emotionalState": "calm but slightly cautious",
        },
        "trainee": {
            "name": "Alex",
            "role": "Software Engineer",
            "personality": ["professional", "responsible"],
            "motivations": [
                "receive compensation that reflects expanded responsibilities",
            ],
            "constraints": ["wants to avoid appearing confrontational"],
            "tendencies": ["prepared to explain additional responsibilities"],
            "knowledge": ["has researched market salaries for similar roles"],
            "emotionalState": "motivated but slightly anxious",
        },
        "language": "English",
        "conversationStart": {
            "speakerRoleId": "employee",
            "initialPromptToUser": (
                "You scheduled this meeting to discuss your compensation. "
                "Start the conversation."
            ),
        },
        "conversationRules": {
            "stayInCharacter": True,
            "allowNarration": False,
            "coachingAllowed": False,
            "tone": "natural professional conversation",
        },
        "conversationDynamics": {
            "typicalBehaviors": [
                "ask the employee to explain expanded responsibilities",
            ],
            "possibleResponses": [
                "mention internal fairness across the team",
            ],
        },
        "decisionConstraints": {
            "maxRaiseWithoutHigherApprovalPercent": 8,
            "alternativeOptions": ["one-time bonus", "promotion pathway discussion"],
        },
        "conversationEndConditions": {
            "possibleEndStates": ["raise approved", "discussion ends without agreement"],
        },
    },
    "evaluationConfig": {
        "learningObjectives": [
            "make a clear compensation request",
            "support the request with evidence",
            "handle objections constructively",
            "work toward a concrete outcome or next step",
        ],
        "evaluationCriteria": [
            {
                "id": "responsibility_articulation",
                "description": (
                    "Trainee clearly explains expanded responsibilities "
                    "and their business impact"
                ),
            },
            {
                "id": "evidence_support",
                "description": (
                    "Trainee references market benchmarks or other evidence"
                ),
            },
            {
                "id": "clear_request",
                "description": "Trainee makes a clear and direct compensation request",
            },
            {
                "id": "handling_pushback",
                "description": "Trainee responds constructively to concerns",
            },
            {
                "id": "progress_toward_outcome",
                "description": "Trainee works toward a concrete outcome",
            },
        ],
        "skillsAssessed": [
            "clear_request",
            "negotiation",
            "evidence_based_persuasion",
            "handling_objections",
            "professional_workplace_communication",
        ],
        "scoring": {
            "scale": "1-5",
            "criteriaWeighting": {
                "responsibility_articulation": 0.2,
                "evidence_support": 0.2,
                "clear_request": 0.2,
                "handling_pushback": 0.2,
                "progress_toward_outcome": 0.2,
            },
        },
        "evaluationInstructionsForLLM": (
            "Evaluate the trainee's performance using the conversation transcript."
        ),
    },
}


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("LEAN_APP_ID", "app")
    monkeypatch.setenv("LEAN_APP_KEY", "key")
    monkeypatch.setenv("LEAN_MASTER_KEY", "master")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_BASE", "https://api.chataiapi.com/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "secret")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_MODEL", "gpt-5-mini")
    monkeypatch.setenv("EVALUATOR_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OBJECTIVE_CHECK_API_KEY", "secret")
    monkeypatch.setenv("OBJECTIVE_CHECK_MODEL", "gpt-5-mini")
    monkeypatch.setenv("STUB_USER_ID", "pilot-user")
    monkeypatch.setenv("ADMIN_ACCESS_TOKEN", "test-admin-token")


class _FakeAdminRecord:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "scenario-new-1")
        self.metadata = kwargs.get("metadata", {})
        self.context = kwargs.get("context", {})
        self.simulationConfig = kwargs.get("simulationConfig", {})
        self.evaluationConfig = kwargs.get("evaluationConfig", {})
        self.status = kwargs.get("status", "draft")
        self.record_status = kwargs.get("recordStatus", "active")
        self.version = kwargs.get("version", "v1")


class _FakeAdminScenarioRepo:
    _created: _FakeAdminRecord | None = None

    async def list_scenarios(self, include_deleted=False):
        records = []
        if self._created:
            records.append(self._created)
        return records

    async def get(self, scenario_id: str):
        if self._created and self._created.id == scenario_id:
            return self._created
        return None

    async def create(self, payload: dict):
        self._created = _FakeAdminRecord(
            id="scenario-new-1",
            metadata=payload.get("metadata", {}),
            context=payload.get("context", {}),
            simulationConfig=payload.get("simulationConfig", {}),
            evaluationConfig=payload.get("evaluationConfig", {}),
            status="draft",
            recordStatus="active",
            version="v1",
        )
        return self._created

    async def update(self, scenario_id: str, payload: dict, *, expected_version=None):
        if self._created and self._created.id == scenario_id:
            return _FakeAdminRecord(
                id=scenario_id,
                metadata=payload.get("metadata", self._created.metadata),
                context=payload.get("context", self._created.context),
                simulationConfig=payload.get(
                    "simulationConfig", self._created.simulationConfig
                ),
                evaluationConfig=payload.get(
                    "evaluationConfig", self._created.evaluationConfig
                ),
                status=payload.get("status", self._created.status),
                recordStatus="active",
                version="v2",
            )
        return None

    async def soft_delete(self, scenario_id: str):
        pass

    async def restore(self, scenario_id: str):
        return None


class _FakeSessionRepo:
    async def list_sessions(self, stub_user_id=None):
        return []


@pytest.fixture(autouse=True)
def _override_deps(monkeypatch):
    fake_repo = _FakeAdminScenarioRepo()
    fake_session_repo = _FakeSessionRepo()

    from app.services.admin import scenarios_service

    monkeypatch.setattr(
        scenarios_service.AdminScenariosService,
        "__init__",
        lambda self, **kwargs: None,
    )

    def _make_service():
        svc = scenarios_service.AdminScenariosService.__new__(
            scenarios_service.AdminScenariosService
        )
        object.__setattr__(svc, "repo", fake_repo)
        object.__setattr__(svc, "session_repo", fake_session_repo)
        return svc

    app.dependency_overrides[admin_scenarios_routes._service] = _make_service
    yield
    app.dependency_overrides.pop(admin_scenarios_routes._service, None)


@pytest.mark.asyncio
async def test_admin_create_with_nested_payload():
    """POST /api/admin/scenarios with the canonical nested payload must succeed."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/scenarios",
            json=CANONICAL_NESTED_PAYLOAD,
            headers={
                "X-Admin-Token": "test-admin-token",
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()

    assert "metadata" in body
    assert body["metadata"]["title"] == (
        "Request a Salary Increase After Taking on Expanded Responsibilities"
    )
    assert "context" in body
    assert "simulationConfig" in body
    assert "evaluationConfig" in body

    assert "skills" not in body
    assert "category" not in body
    assert "description" not in body
    assert "objective" not in body
    assert "aiPersona" not in body
    assert "traineePersona" not in body


@pytest.mark.asyncio
async def test_admin_create_rejects_legacy_flat_payload():
    """POST /api/admin/scenarios with legacy flat fields must be rejected."""
    legacy_payload = {
        "category": "Feedback",
        "title": "Old Scenario",
        "description": "Old description",
        "objective": "Old objective",
        "aiPersona": {"name": "AI"},
        "traineePersona": {"name": "Trainee"},
        "endCriteria": ["Done"],
        "skills": ["skill-1"],
        "prompt": "Old prompt",
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/scenarios",
            json=legacy_payload,
            headers={
                "X-Admin-Token": "test-admin-token",
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_admin_create_validates_nested_substructures():
    """Create must require metadata, context, simulationConfig, evaluationConfig."""
    incomplete_payload = {
        "metadata": {
            "title": "Incomplete",
            "slug": "incomplete",
        },
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/scenarios",
            json=incomplete_payload,
            headers={
                "X-Admin-Token": "test-admin-token",
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_admin_list_returns_nested_schema():
    """GET /api/admin/scenarios must return nested schema items."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/admin/scenarios",
            json=CANONICAL_NESTED_PAYLOAD,
            headers={"X-Admin-Token": "test-admin-token"},
        )

        response = await client.get(
            "/api/admin/scenarios",
            headers={"X-Admin-Token": "test-admin-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "scenarios" in body

    if body["scenarios"]:
        item = body["scenarios"][0]
        assert "metadata" in item
        assert "context" in item
        assert "simulationConfig" in item
        assert "evaluationConfig" in item
        assert "skills" not in item
        assert "skillSummaries" not in item


@pytest.mark.asyncio
async def test_admin_update_with_nested_payload():
    """PUT /api/admin/scenarios/{id} with nested payload must succeed."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/admin/scenarios",
            json=CANONICAL_NESTED_PAYLOAD,
            headers={"X-Admin-Token": "test-admin-token"},
        )
        scenario_id = create_resp.json().get("id", "scenario-new-1")

        updated = dict(CANONICAL_NESTED_PAYLOAD)
        updated["metadata"] = {
            **updated["metadata"],
            "title": "Updated Salary Negotiation",
        }

        response = await client.put(
            f"/api/admin/scenarios/{scenario_id}",
            json=updated,
            headers={
                "X-Admin-Token": "test-admin-token",
                "If-Match": "v1",
            },
        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["metadata"]["title"] == "Updated Salary Negotiation"


@pytest.mark.asyncio
async def test_admin_publish_validates_nested_schema():
    """Publish must validate the nested schema, not legacy flat fields."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/admin/scenarios",
            json=CANONICAL_NESTED_PAYLOAD,
            headers={"X-Admin-Token": "test-admin-token"},
        )
        scenario_id = create_resp.json().get("id", "scenario-new-1")

        response = await client.post(
            f"/api/admin/scenarios/{scenario_id}/publish",
            headers={"X-Admin-Token": "test-admin-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "published"
    assert "metadata" in body
    assert "evaluationConfig" in body
