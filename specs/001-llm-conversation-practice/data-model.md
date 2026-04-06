# Data Model

LeanCloud provides schemaless collections but we will treat each entity as a strongly typed record so
FastAPI + frontend clients can rely on contracts.

## Scenario
- `id` (string) — primary key.
- `metadata` (object, required)
    - `title` (string, required)
    - `slug` (string, required)
    - `domain` (string, required)
    - `scenarioType` (string, required)
    - `difficulty` (string, required)
    - `conflictLevel` (string, required)
    - `estimatedDurationMinutes` (int, required)
    - `tags` (array[string], required)
- `context` (object, required)
    - `situation` (string, required)
    - `background` (string, required)
    - `setting` (string, required)
- `simulationConfig` (object, required)
    - `ai` (object, required) — `{name, role, personality[], motivations[], constraints[], tendencies[], knowledge[], emotionalState}`
    - `trainee` (object, required) — `{name, role, personality[], motivations[], constraints[], tendencies[], knowledge[], emotionalState}`
    - `language` (string, required)
    - `conversationStart` (object, required) — `{speakerRoleId, initialPromptToUser}`
    - `conversationRules` (object, required) — `{stayInCharacter, allowNarration, coachingAllowed, tone}`
    - `conversationDynamics` (object, required) — `{typicalBehaviors[], possibleResponses[]}`
    - `decisionConstraints` (object, required) — `{maxRaiseWithoutHigherApprovalPercent?, alternativeOptions[]}`
    - `conversationEndConditions` (object, required) — `{possibleEndStates[]}`
- `evaluationConfig` (object, required)
    - `learningObjectives` (array[string], required)
    - `evaluationCriteria` (array[object], required) — `{id, description}`
    - `skillsAssessed` (array[string], required)
    - `scoring` (object, required) — `{scale, criteriaWeighting}`
    - `evaluationInstructionsForLLM` (string, required)
- `status` (enum: `draft` | `published`)
- `createdAt/updatedAt` — timestamps.

Relationships: `Scenario` referenced by `PracticeSession` (1:N) and `Turn` (through session).
Validation: enforce nested presence for all canonical fields before publish.
Note: legacy `skills`, `skillSummaries`, `aiPersona`, `traineePersona`, `objective`, `endCriteria`, and `prompt` are removed.

## Skill
- `id` (string, required, unique) — deterministic identifier used by seed scripts and tests to join scenarios ↔ skills.
- `name` (string, required, unique) — label shown in the UI/evaluations.
- `category` (string, required) — taxonomy bucket for filtering (e.g., `Feedback`, `Conflict`).
- `rubric` (string, required) — markdown text describing ratings 1–5.
- `description` (string, optional) — additional context for admins.
- `createdAt/updatedAt`.

Skills are seeded/administered via the Admin Data Management API. Scenarios include skill labels in `evaluationConfig.skillsAssessed` to define assessment scope.

## PracticeSession
- `id` (string)
- `scenarioId` (string, required) — reference to Scenario.
- `stubUserId` (string, required, constant) — scopes history.
- `clientSessionStartedAt` (date, required) — timestamp provided by the client to measure drift.
- `status` (enum: `pending`, `active`, `ended`).
- `terminationReason` (enum) — `manual`, `idle`, `duration`, `objective_met`, `objective_failed`.
- `objectiveStatus` (enum: `unknown`, `succeeded`, `failed`).
- `objectiveReason` (string, optional) — last explanation returned by the goal-check model when it decided to end the session.
- `evaluationId` (string, optional) — reference to Evaluation.
- `wsChannel` (string) — channel/room ID for WebSocket pushes.
- `createdAt/updatedAt`.

Relationships: `PracticeSession` owns `Turn` records (1:N) and a single `Evaluation`. Hard deletes
cascade to dependent records and media storage; deletion removes the record
entirely.

State transitions:
`pending` → `active` when AI initiates turn 0.  
`active` → `ended` when one of termination criteria occurs.  

## Turn
- `id` (string)
- `sessionId` (string, required).
- `sequence` (int, required, unique per session) — 0-based; AI turn 0 for initiation.
- `speaker` (enum: `ai`, `trainee`).
- `audioFileId` (string, required) — media storage ID.
- `audioUrl` (virtual) — rendered in API responses as a short-lived signed URL; not stored in the Turn record.
- `transcript` (string, optional) — AI transcript persists immediately; trainee transcript may be
  null/placeholder until ASR finishes (tracked via `asrStatus` below).
- `context` (string, optional) — trainee-supplied metadata, echoed back to clients.
- `asrStatus` (enum: `pending`, `completed`, `failed`) — trainee turns only.
- `startedAt` / `endedAt` (dates, required) — timestamps supplied by client per turn; server stores validated versions for drift enforcement.
- `createdAt` (date) — first persisted time; used for idle/duration enforcement.
- `latencyMs` (int) — server measured for observability; exposed in telemetry APIs.

Constraints: MP3 blob stored in media storage (<128 KB). Insert order must match `sequence`,
enforced via unique index per session + server-authoritative increments. Retries reuse same sequence
number if ASR fails.

## Evaluation
- `id` (string)
- `sessionId` (string, required, unique) — 1:1 relationship.
- `status` (enum: `pending`, `running`, `failed`, `completed`).
- `scores` (array[object]) — each `{skillId, rating (1-5), note}` derived from scenario skills.
- `summary` (string) — strengths/gaps paragraph.
- `evaluatorModel` (string) — identifier for the LLM config used.
- `attempts` (int) — increments on each retry/backoff cycle.
- `lastError` (string, optional) — truncated message for `failed` state.
- `queuedAt` / `completedAt`.

Worker interaction: FastAPI marks the evaluation as `pending` and spins up an in-process background
task that reads the record, performs scoring, and updates state. If the process
restarts mid-flight, the trainee can requeue the job via API to spawn a fresh task.

## Supporting Concepts

### Webhook / Event Payloads
- `TerminationEvent`: `{sessionId, reason, terminatedAt, latencyMs}` pushed via WebSocket + fallback
  polling; clients trust server reason/time.
- `EvaluationReadyEvent`: `{sessionId, evaluationId}` when `status` transitions to `completed`.

### Observability Fields
All entities capture `sessionId`, `turnId`, and `traceId` metadata in logs/metrics; these map to
OpenTelemetry spans described in the Observability & Metrics Contract.
