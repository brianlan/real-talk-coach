"""Red-phase contract tests for session and scenario endpoints.

These tests encode the canonical nested scenario shape and assert that
API responses use the new schema without legacy fields.  They are
expected to FAIL until the production code is refactored.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import status

from datetime import datetime, timezone

from app.api.routes import scenarios as scenarios_routes
from app.api.routes import sessions as sessions_routes
from app.main import app
from app.repositories.session_repository import PracticeSessionRecord


created_session_payload: dict | None = None


# ---------------------------------------------------------------------------
# Canonical nested scenario fixture
# ---------------------------------------------------------------------------

def _make_nested_scenario_doc(**overrides):
    """Minimal nested scenario doc matching the canonical shape."""
    doc = {
        "id": "scenario-1",
        "metadata": {
            "title": "Request a Salary Increase After Taking on Expanded Responsibilities",
            "slug": "salary-raise-expanded-responsibilities",
            "domain": "Workplace",
            "scenarioType": "Negotiation",
            "difficulty": "Medium",
            "conflictLevel": "Medium",
            "estimatedDurationMinutes": 8,
            "tags": ["salary negotiation"],
        },
        "context": {
            "situation": "An employee has taken on significant additional responsibilities.",
            "background": "The company is currently facing moderate budget pressure.",
            "setting": "A scheduled one-on-one meeting.",
        },
        "simulationConfig": {
            "ai": {
                "name": "Jordan",
                "role": "Engineering Manager",
                "personality": ["professional"],
                "motivations": ["retain high-performing employees"],
                "constraints": ["budget is tight"],
                "tendencies": ["initially cautious"],
                "knowledge": ["employee has taken on additional work"],
                "emotionalState": "calm",
            },
            "trainee": {
                "name": "Alex",
                "role": "Software Engineer",
                "personality": ["professional"],
                "motivations": ["receive fair compensation"],
                "constraints": ["avoid being confrontational"],
                "tendencies": ["prepared to explain"],
                "knowledge": ["has researched market salaries"],
                "emotionalState": "motivated",
            },
            "language": "English",
            "conversationStart": {
                "speakerRoleId": "employee",
                "initialPromptToUser": "Start the conversation.",
            },
            "conversationRules": {
                "stayInCharacter": True,
                "allowNarration": False,
                "coachingAllowed": False,
                "tone": "natural professional conversation",
            },
            "conversationDynamics": {
                "typicalBehaviors": ["ask for examples"],
                "possibleResponses": ["mention fairness"],
            },
            "decisionConstraints": {
                "maxRaiseWithoutHigherApprovalPercent": 8,
                "alternativeOptions": ["bonus"],
            },
            "conversationEndConditions": {
                "possibleEndStates": ["raise approved"],
            },
        },
        "evaluationConfig": {
            "learningObjectives": ["make a clear request"],
            "evaluationCriteria": [
                {"id": "clear_request", "description": "Makes a clear request"},
            ],
            "skillsAssessed": ["clear_request", "negotiation"],
            "scoring": {"scale": "1-5", "criteriaWeighting": {"clear_request": 1.0}},
            "evaluationInstructionsForLLM": "Evaluate the trainee.",
        },
    }
    doc.update(overrides)
    return doc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


@pytest.fixture(autouse=True)
def _override_repo(monkeypatch):
    global created_session_payload
    nested_doc = _make_nested_scenario_doc()

    async def _list_published(*args, **kwargs):
        # Return the nested doc wrapped in a namespace-like object
        # that exposes nested fields as attributes
        return [_NestedScenario(**nested_doc)]

    async def _get(*args, **kwargs):
        return None

    class FakeRepo:
        list_published = staticmethod(_list_published)
        get = staticmethod(_get)

    created_session: PracticeSessionRecord | None = None

    async def _list_sessions(stub_user_id=None):
        return []

    async def _create_session(payload):
        global created_session_payload
        nonlocal created_session
        created_session_payload = dict(payload)
        created_session = PracticeSessionRecord(
            id="session-1",
            scenario_id=payload["scenarioId"],
            stub_user_id=payload["stubUserId"],
            language=payload.get("language", "en"),
            opening_prompt=payload.get("openingPrompt", "Hello"),
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
            mode=payload.get("mode", "turn_based"),
        )
        return created_session

    async def _update_session(session_id, payload):
        nonlocal created_session
        if created_session is not None:
            return PracticeSessionRecord(
                id=session_id,
                scenario_id=created_session.scenario_id,
                stub_user_id=created_session.stub_user_id,
                language=created_session.language,
                opening_prompt=created_session.opening_prompt,
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
                mode=payload.get("mode", created_session.mode),
            )
        return PracticeSessionRecord(
            id=session_id,
            scenario_id="scenario-1",
            stub_user_id="pilot-user",
            language="en",
            opening_prompt="Hello",
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
            mode=payload.get("mode", "turn_based"),
        )

    class FakeSessionRepo:
        list_sessions = staticmethod(_list_sessions)
        create_session = staticmethod(_create_session)
        update_session = staticmethod(_update_session)

    class FakeScenarioRepo:
        async def get(self, scenario_id: str):
            return _NestedScenario(**_make_nested_scenario_doc())

    app.dependency_overrides[scenarios_routes._repo] = lambda: FakeRepo()
    app.dependency_overrides[sessions_routes._repo] = lambda: FakeSessionRepo()
    app.dependency_overrides[sessions_routes._scenario_repo] = lambda: FakeScenarioRepo()

    yield
    created_session_payload = None
    app.dependency_overrides.pop(scenarios_routes._repo, None)
    app.dependency_overrides.pop(sessions_routes._repo, None)
    app.dependency_overrides.pop(sessions_routes._scenario_repo, None)


class _NestedScenario:
    """Lightweight namespace that exposes the canonical nested shape as attributes.

    Uses snake_case attribute names matching the production Scenario dataclass,
    so the public _scenario_response serializer can read them correctly.
    """

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")
        self.status = kwargs.get("status", "published")
        self.metadata = kwargs.get("metadata", {})
        self.context = kwargs.get("context", {})
        self.simulation_config = kwargs.get("simulationConfig", {})
        self.evaluation_config = kwargs.get("evaluationConfig", {})
        self.idle_limit_seconds = kwargs.get("idle_limit_seconds")
        self.duration_limit_seconds = kwargs.get("duration_limit_seconds")


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_session_missing_timestamps_rejected():
    payload = {"scenarioId": "scenario-1"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_list_scenarios_returns_nested_schema():
    """GET /api/scenarios must return nested metadata/context/simulationConfig/evaluationConfig."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/scenarios", params={"historyStepCount": 1})

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert "items" in payload
    items = payload["items"]
    assert len(items) >= 1

    item = items[0]

    # New nested top-level keys must exist
    assert "metadata" in item
    assert "context" in item
    assert "simulationConfig" in item
    assert "evaluationConfig" in item

    # metadata substructure
    assert item["metadata"]["title"] == (
        "Request a Salary Increase After Taking on Expanded Responsibilities"
    )
    assert item["metadata"]["domain"] == "Workplace"
    assert item["metadata"]["scenarioType"] == "Negotiation"

    # simulationConfig substructure
    assert "ai" in item["simulationConfig"]
    assert "trainee" in item["simulationConfig"]
    assert "conversationStart" in item["simulationConfig"]
    assert item["simulationConfig"]["ai"]["name"] == "Jordan"

    # evaluationConfig substructure
    assert "evaluationCriteria" in item["evaluationConfig"]
    assert "skillsAssessed" in item["evaluationConfig"]

    # Legacy keys must NOT exist
    assert "skills" not in item
    assert "skillSummaries" not in item
    assert "category" not in item
    assert "description" not in item
    assert "objective" not in item
    assert "aiPersona" not in item
    assert "traineePersona" not in item
    assert "endCriteria" not in item
    assert "prompt" not in item


@pytest.mark.asyncio
async def test_skills_endpoint_removed():
    """GET /api/skills must be gone after cutover (no Skill collection dependency)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/skills")

    assert response.status_code == status.HTTP_404_NOT_FOUND


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
async def test_create_session_realtime_mode_is_persisted():
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "scenarioId": "scenario-1",
        "clientSessionStartedAt": now,
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    assert created_session_payload is not None
    assert created_session_payload["mode"] == "realtime"


@pytest.mark.asyncio
async def test_create_session_rejects_incomplete_scenario():
    now = datetime.now(timezone.utc).isoformat()
    payload = {"scenarioId": "scenario-1", "clientSessionStartedAt": now}

    class BrokenScenarioRepo:
        async def get(self, scenario_id: str):
            return _NestedScenario(
                **_make_nested_scenario_doc(
                    context={},
                    simulationConfig={
                        "trainee": {
                            "name": "Alex",
                            "role": "Software Engineer",
                        }
                    },
                )
            )

    app.dependency_overrides[sessions_routes._scenario_repo] = lambda: BrokenScenarioRepo()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/sessions", json=payload)
    finally:
        app.dependency_overrides.pop(sessions_routes._scenario_repo, None)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body = response.json()
    assert "detail" in body
    assert "simulationConfig.ai" in body["detail"]
