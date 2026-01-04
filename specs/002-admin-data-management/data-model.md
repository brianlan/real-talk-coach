# Data Model: Admin Data Management

## Admin User
- `id` — unique admin identifier.
- `name` — display name for audit entries.
- `email` — contact identifier.
- `status` — `active` or `disabled`.

Validation: only `active` admins may access management pages.

## Audit Log
- `id` — unique identifier.
- `adminId` — admin reference.
- `action` — `create`, `update`, `delete`.
- `entityType` — `skill`, `scenario`, `session`.
- `entityId` — entity reference.
- `timestamp` — action time.
- `details` — summary of changes (optional).

Validation: audit log entries are created for all admin create/update/delete actions.

## Skill
- `id` — unique identifier.
- `name` — display label.
- `category` — grouping label.
- `rubric` — rating guidance text.
- `description` — optional notes.
- `status` — `active` or `deleted` (soft delete).
- `createdAt/updatedAt` — timestamps.

Validation:
- `name`, `category`, `rubric` required.
- `name` unique within tenant.

Rules:
- Soft delete only; restore allowed.
- Deletion blocked if referenced by any published scenario; response includes impacted scenarios.

## Scenario
- `id` — unique identifier.
- `category` — taxonomy label.
- `title` — display title.
- `description` — scenario context.
- `objective` — success criteria text.
- `aiPersona` — `{name, role, background}`.
- `traineePersona` — `{name, role, background}`.
- `endCriteria` — ordered list of stop conditions.
- `prompt` — initiation prompt text.
- `skills` — ordered list of skill IDs.
- `idleLimitSeconds` — optional override.
- `durationLimitSeconds` — optional override.
- `status` — `draft` or `published`.
- `recordStatus` — `active` or `deleted` (soft delete).
- `createdAt/updatedAt` — timestamps.

Validation:
- Required fields must be present before publish.
- `skills` must contain at least one unique skill ID.

Rules:
- Publishing blocked if required fields are missing or `skills` is empty.
- Scenario deletion is soft delete only.
- Scenario deletion blocked if any sessions exist for the scenario.

## Practice Session (Admin View)
- `id` — unique identifier.
- `scenarioId` — scenario reference.
- `status` — `pending`, `active`, `ended`.
- `startedAt/endedAt` — timestamps.
- `terminationReason` — reason code.
- `evaluationStatus` — `pending`, `running`, `failed`, `completed`.
- `createdAt` — session creation time.

Admin actions:
- Filter by date range, scenario, and status.
- View transcripts and evaluation summary.
- Delete session with confirmation (cascade to related records).

## Evaluation (Admin View)
- `id` — unique identifier.
- `sessionId` — session reference.
- `status` — `pending`, `running`, `failed`, `completed`.
- `scores` — list of `{skillId, rating, note}`.
- `summary` — narrative feedback.
- `attempts` — retry count.
- `completedAt` — timestamp.

## Relationships

- Scenario 1:N PracticeSession
- PracticeSession 1:N Turn (read-only in admin)
- PracticeSession 1:1 Evaluation
- Skill N:N Scenario (ordered list per scenario)

## State Transitions

- Scenario: `draft` ↔ `published`.
- Record status: `active` ↔ `deleted` (soft delete/restore).
- Session: `pending` → `active` → `ended` (admin read-only).
- Evaluation: `pending` → `running` → `completed`/`failed` (admin read-only).
