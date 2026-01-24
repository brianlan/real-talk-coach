# Implementation Plan: Admin Data Management

**Branch**: `002-admin-data-management` | **Date**: 2025-12-30 | **Spec**: `specs/002-admin-data-management/spec.md`
**Input**: Feature specification from `/specs/002-admin-data-management/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Constitution gates below must
be satisfied before moving forward.

## Summary

Deliver admin-only management pages and APIs to create and maintain skills, scenarios, and session
records with validation, safe deletes, and audit logging. The plan extends the existing FastAPI API
surface with admin-scoped CRUD endpoints and adds a Next.js admin UI for data setup and oversight,
while preserving trainee flows and data integrity.

## Technical Context

**Language/Version**: Backend Python 3.11 (FastAPI); Frontend TypeScript/Next.js 15
**Primary Dependencies**: FastAPI, Uvicorn, httpx, LeanCloud REST APIs, Next.js/React
**Storage**: LeanCloud LObject/LFile for structured data + media references
**Testing**: Pytest + httpx AsyncClient; Vitest + Testing Library + Playwright. Latest run (2026-01-24): `pytest`, `pnpm test`, `pnpm playwright` passed.
**Target Platform**: Web app (admin UI) + Linux server (API)
**Project Type**: Full-stack web (separate backend + frontend packages)
**Performance Goals**: Admin list/search results visible within 2 seconds for typical datasets (<1k records)
**Constraints**: Admin actions require a pre-shared token; destructive actions require confirmation; audit log for CRUD actions
**Scale/Scope**: Internal admin users; low concurrency; hundreds of skills/scenarios; thousands of sessions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Readability & Explicitness: CRUD flows and validation errors are explicit; no hidden side effects.
- TDD-First & Isolated: Contract/integration tests stub LeanCloud and verify auth, validation,
  concurrency checks, and delete rules before implementation.
- Automation Everywhere: Reuse existing lint/test commands (ruff/pytest, pnpm lint/test/playwright)
  and add admin coverage to CI scripts.
- Simple, Disciplined Design: Extend existing repositories/routes instead of new service layers.
- Purposeful Comments & Rationale: Capture reasons for auth, soft deletes, and audit logging.

## Project Structure

### Documentation (this feature)

```text
specs/002-admin-data-management/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── tasks/
│   └── telemetry/
└── tests/
    ├── unit/
    ├── contract/
    └── integration/

frontend/
├── app/
├── components/
├── services/
├── state/
└── tests/
    ├── unit/
    └── e2e/
```

**Structure Decision**: Reuse existing `backend/` and `frontend/` workspaces to keep deployment and
Tooling consistent while adding admin routes and pages in place.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None_ | – | – |

## Phase 0 – Outline & Research

**Inputs captured from Technical Context**
- Dependencies: FastAPI, httpx, LeanCloud REST, Next.js/React.
- Integrations: LeanCloud LObject/LFile, existing session deletion cascade, audit logging.

**Research tasks dispatched**
- Best practices for admin CRUD flows with destructive-action confirmation and audit logs.
- Patterns for pre-shared token admin access in internal tools with low ops overhead.
- Approaches for optimistic concurrency checks in admin CRUD.

**Output**: `specs/002-admin-data-management/research.md`

## Phase 1 – Design & Contracts

**Artifacts produced**
- `specs/002-admin-data-management/data-model.md`: Entities and validation for skills, scenarios,
  sessions, evaluations, and audit logs.
- `specs/002-admin-data-management/contracts/openapi.yaml`: Admin CRUD endpoints, filters,
  validation errors, and concurrency conflicts.
- `specs/002-admin-data-management/quickstart.md`: Admin setup, environment vars, local run/test.
- Agent context updated via `.specify/scripts/bash/update-agent-context.sh codex`.

**Design highlights**
- Admin endpoints live under `/api/admin` with a pre-shared token header and explicit 401/403
  behavior for missing or invalid tokens.
- Skills/scenarios use soft-delete with restore; deletions are blocked when referenced by published
  scenarios or when sessions exist for a scenario.
- Updates enforce optimistic concurrency and return a conflict error when the record has changed.
- Audit log entries are recorded for admin create/update/delete actions.

## Phase 2 – Implementation Plan (Preview)

Will break into incremental stories during `/speckit.tasks`, roughly:
1. **Admin auth + scaffolding**: admin routing, token checks, shared error handling, admin shell.
2. **Skill management**: CRUD API + UI, soft delete/restore, reference checks, tests.
3. **Scenario management**: CRUD + publish/unpublish, skill ordering, validation, soft delete.
4. **Session oversight**: list/detail/delete, evaluation visibility, deletion block rules, tests.
5. **Audit logging**: create/update/delete logging with filters for review.
6. **Testing/automation**: contract + integration + UI tests for admin flows.

## Constitution Check (Post-Design)

- Readability & Explicitness: Contracts and data model define validation, conflicts, and delete
  rules explicitly.
- TDD-First & Isolated: Tests specify required mocks for LeanCloud and admin auth.
- Automation Everywhere: Quickstart lists lint/test commands and admin e2e coverage.
- Simple, Disciplined Design: Admin features extend existing patterns without new service layers.
- Purposeful Comments & Rationale: Rationale for auth, soft deletes, and audit logging captured.
