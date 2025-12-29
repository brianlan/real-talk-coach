# Implementation Plan: Admin Data Management

**Branch**: `002-admin-data-management` | **Date**: 2025-12-29 | **Spec**: `specs/002-admin-data-management/spec.md`
**Input**: Feature specification from `/specs/002-admin-data-management/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Constitution gates below must
be satisfied before moving forward.

## Summary

Deliver admin-only management pages and APIs that let internal operators create and maintain skills,
scenarios, and session data (including safe deletes), with clear validation and search/filtering.
The approach extends the existing FastAPI backend with admin-scoped CRUD endpoints and adds a
Next.js admin UI for skills, scenarios, and sessions, while preserving current trainee flows.

## Technical Context

**Language/Version**: Backend Python 3.11 (FastAPI); Frontend TypeScript/Next.js 15
**Primary Dependencies**: FastAPI, Uvicorn, httpx, LeanCloud REST APIs, Next.js/React
**Storage**: LeanCloud LObject/LFile for structured data + media references
**Testing**: Pytest + httpx AsyncClient; Vitest + Testing Library + Playwright
**Target Platform**: Web app (admin UI) + Linux server (API)
**Project Type**: Full-stack web (separate backend + frontend packages)
**Performance Goals**: Admin list/search results visible within 2 seconds for typical datasets (<1k records)
**Constraints**: Admin actions must be auditable in logs; destructive actions require confirmation
**Scale/Scope**: Internal admin users; low concurrency; hundreds of skills/scenarios; thousands of sessions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Readability & Explicitness: Endpoints and UI flows follow clear CRUD patterns with explicit
  validation and error messages; no implicit side effects.
- TDD-First & Isolated: Contract and integration tests will stub LeanCloud and verify admin-only
  access, validation failures, and delete cascades before implementation.
- Automation Everywhere: Reuse existing lint/test commands (ruff/pytest, pnpm lint/test/playwright)
  and add admin flow coverage to CI scripts.
- Simple, Disciplined Design: Extend existing repositories and routes; avoid new services unless
  repeated needs prove it.
- Purposeful Comments & Rationale: Document why admin auth and delete safeguards were chosen.

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

**Structure Decision**: Reuse existing `backend/` and `frontend/` workspaces and add admin routes
and pages within those directories to keep deployment and tooling consistent.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None_ | – | – |

## Phase 0 – Outline & Research

**Inputs captured from Technical Context**
- Dependencies: FastAPI, httpx, LeanCloud REST, Next.js/React.
- Integrations: LeanCloud LObject/LFile, existing session cleanup and evaluation references.

**Research tasks dispatched**
- Best practices for admin CRUD flows with destructive-action safeguards.
- Patterns for admin-only access control in internal tools with low operational overhead.
- Approaches to prevent breaking published scenario/skill references while allowing edits.

**Output**: `specs/002-admin-data-management/research.md`

## Phase 1 – Design & Contracts

**Artifacts produced**
- `specs/002-admin-data-management/data-model.md`: Admin-facing entities, constraints, and state rules.
- `specs/002-admin-data-management/contracts/openapi.yaml`: Admin CRUD endpoints, filters, validation errors.
- `specs/002-admin-data-management/quickstart.md`: Admin setup, environment variables, and local run/test steps.
- Agent context updated via `.specify/scripts/bash/update-agent-context.sh codex`.

**Design highlights**
- Admin endpoints are separated under an `/api/admin` prefix with explicit authorization and
  validation errors aligned to the spec.
- Skills and scenarios use safe-delete checks to prevent orphaned references; blocking responses list
  affected records to guide admins.
- Session delete actions reuse the existing cascade behavior to remove evaluations and media
  references, with confirmation required at the UI layer.

## Phase 2 – Implementation Plan (Preview)

Will break into incremental stories during `/speckit.tasks`, roughly:
1. **Admin auth + scaffolding**: secure admin routes, shared error handling, add admin navigation shell.
2. **Skill management**: CRUD API + UI, reference checks, and tests.
3. **Scenario management**: CRUD + publish/unpublish, skill assignment ordering, validation.
4. **Session oversight**: list/detail/delete, evaluation status visibility, cleanup confirmation.
5. **Testing/automation**: contract + integration + UI tests for core admin flows.

## Constitution Check (Post-Design)

- Readability & Explicitness: Contracts and data model define explicit validation rules and error flows.
- TDD-First & Isolated: Tests specify required mocks for LeanCloud and admin auth.
- Automation Everywhere: Quickstart lists lint/test commands and admin e2e coverage.
- Simple, Disciplined Design: Admin features extend existing patterns without new service layers.
- Purposeful Comments & Rationale: Rationale for auth and delete constraints captured in docs.
