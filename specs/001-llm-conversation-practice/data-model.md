# Data Model

LeanCloud provides schemaless collections but we will treat each entity as a strongly typed record so
FastAPI + frontend clients can rely on contracts.

## Scenario
- `objectId` (string, LeanCloud-generated) — primary key.
- `category` (string, required) — taxonomy label (e.g., "Difficult Feedback").
- `title` (string, required, unique per tenant) — <= 120 chars.
- `description` (string, required) — markdown-capable narrative.
- `objective` (string, required) — explicit success criteria text.
- `aiPersona` (object, required) — `{name, role, background}` describing the AI roleplayer.
- `traineePersona` (object, required) — metadata surfaced to trainee.
- `endCriteria` (array[string], required, min 1) — textual stop conditions shown to objective checker.
- `skills` (array[string], required) — skill IDs from global library that drive evaluation rubric.
- `idleLimitSeconds` (int, optional, default 8) — overrides contract default if set.
- `durationLimitSeconds` (int, optional, default 300) — overrides contract default if set.
- `prompt` (string, required) — system/prompt text for AI initiation turn.
- `status` (enum: `draft` | `published`) — only `published` scenarios appear in catalog.
- `createdAt/updatedAt` — LeanCloud timestamps.

Relationships: `Scenario` referenced by `PracticeSession` (1:N) and `Turn` (through session).

Validation: enforce presence of persona/background/endCriteria before publish; idle/duration limits
clamped to positive values and <= 900 seconds to prevent abuse.

## PracticeSession
- `objectId`
- `scenarioId` (pointer → Scenario, required).
- `stubUserId` (string, required, constant) — scopes history.
- `clientSessionStartedAt` (date, required) — timestamp provided by the client to measure drift.
- `status` (enum: `pending`, `active`, `ended`).
- `terminationReason` (enum) — `manual`, `idle`, `duration`, `objective_met`, `objective_failed`,
  `qa_error`, `media_error`.
- `startedAt` / `endedAt` (dates) — server source-of-truth timestamps recorded when AI turn 0 is issued / session terminates; compared against `clientSessionStartedAt` to enforce drift rules.
- `totalDurationSeconds` (int) — server-calculated; validated against drift rule.
- `idleLimitSeconds` / `durationLimitSeconds` (ints) — cached from scenario/client with overrides.
- `objectiveStatus` (enum: `unknown`, `succeeded`, `failed`).
- `evaluationId` (pointer → Evaluation, optional).
- `wsChannel` (string) — channel/room ID for WebSocket pushes.
- `createdAt/updatedAt`.

Relationships: `PracticeSession` owns `Turn` records (1:N) and a single `Evaluation`. Hard deletes
cascade to dependent records and LeanCloud files via backend orchestrator; deletion removes the record
entirely, so `deleted` never surfaces via API responses.

State transitions:
`pending` → `active` when AI initiates turn 0.  
`active` → `ended` when one of termination criteria occurs.  
Deletion removes `PracticeSession`, its turns, evaluation, and LeanCloud files immediately; there is
no lingering soft-deleted state exposed to clients.

## Turn
- `objectId`
- `sessionId` (pointer → PracticeSession, required).
- `sequence` (int, required, unique per session) — 0-based; AI turn 0 for initiation.
- `speaker` (enum: `ai`, `trainee`).
- `audioFileId` (string, required) — LeanCloud LFile ID (only persisted field; signed URLs are minted on demand when serving API responses so they never expire in storage).
- `audioUrl` (virtual) — rendered in API responses as a short-lived signed URL; not stored in the Turn record.
- `transcript` (string, optional) — AI transcript persists immediately; trainee transcript may be
  null/placeholder until ASR finishes (tracked via `asrStatus` below).
- `context` (string, optional) — trainee-supplied metadata.
- `asrStatus` (enum: `pending`, `completed`, `failed`) — trainee turns only.
- `createdAt` (date) — first persisted time; used for idle/duration enforcement.
- `latencyMs` (int) — server measured for observability.

Constraints: MP3 blob stored as LeanCloud LFile (<128 KB). Insert order must match `sequence`,
enforced via unique index per session + server-authoritative increments. Retries reuse same sequence
number if ASR fails.

## Evaluation
- `objectId`
- `sessionId` (pointer → PracticeSession, required, unique) — 1:1 relationship.
- `status` (enum: `pending`, `running`, `failed`, `completed`).
- `scores` (array[object]) — each `{skillId, rating (1-5), note}` derived from scenario skills.
- `summary` (string) — strengths/gaps paragraph.
- `evaluatorModel` (string) — identifier for the LLM config used.
- `attempts` (int) — increments on each retry/backoff cycle.
- `lastError` (string, optional) — truncated message for `failed` state.
- `queuedAt` / `completedAt`.

Worker interaction: FastAPI marks the evaluation as `pending` and spins up an in-process background
task that reads the record, performs scoring, and updates state via LeanCloud REST. If the process
restarts mid-flight, the trainee can requeue the job via API to spawn a fresh task.

## Supporting Concepts

### Webhook / Event Payloads
- `TerminationEvent`: `{sessionId, reason, terminatedAt, latencyMs}` pushed via WebSocket + fallback
  polling; clients trust server reason/time.
- `EvaluationReadyEvent`: `{sessionId, evaluationId}` when `status` transitions to `completed`.

### Observability Fields
All entities capture `sessionId`, `turnId`, and `traceId` metadata in logs/metrics; these map to
OpenTelemetry spans described in the Observability & Metrics Contract.
