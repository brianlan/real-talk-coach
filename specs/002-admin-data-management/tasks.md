# Tasks: Admin Data Management

**Input**: Design documents from `/specs/002-admin-data-management/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Latest run (2026-01-24) — backend `pytest` passed; frontend `pnpm test` passed; frontend `pnpm playwright` passed.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal scaffolding for admin UI and configuration

- [X] T001 Update admin token placeholders in `backend/.env.example` and `frontend/.env.local.example`
- [X] T002 Add admin layout shell and navigation in `frontend/app/admin/layout.tsx` and `frontend/components/admin/AdminNav.tsx`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add admin token settings/validation in `backend/app/config.py`
- [X] T004 Implement admin auth dependency in `backend/app/api/deps/admin_auth.py` and wire `/api/admin` routing in `backend/app/api/router.py`
- [X] T005 Create admin API router scaffold in `backend/app/api/routes/admin/router.py` and `backend/app/api/routes/admin/__init__.py`
- [X] T006 Add audit log model/repository/service in `backend/app/models/admin.py`, `backend/app/repositories/audit_log_repository.py`, and `backend/app/services/audit_log_service.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Manage skill library (Priority: P1) 🎯 MVP

**Goal**: Admins can create, edit, soft-delete, restore, and search skills for scenario use.

**Independent Test**: Create a skill, edit it, soft-delete and restore it, and verify skill lists and reference checks update correctly.

### Tests for User Story 1 (write first)

- [X] T027 [P] [US1] Contract tests for admin skills API (CRUD, soft delete/restore, conflicts) in `backend/tests/contract/test_admin_skills.py`
- [X] T028 [US1] Integration test for skill create/edit/delete/restore with optimistic concurrency in `backend/tests/integration/test_admin_skills_flow.py`
- [X] T029 [P] [US1] E2E test for admin skills UI (create/edit/delete/restore) in `frontend/tests/e2e/admin-skills.spec.ts`

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement skill repository CRUD + soft delete/restore in `backend/app/repositories/skill_repository.py`
- [X] T008 [US1] Implement admin skills service (validation, concurrency, audit log) in `backend/app/services/admin/skills_service.py`
- [X] T009 [US1] Implement admin skills routes in `backend/app/api/routes/admin/skills.py`
- [X] T010 [P] [US1] Add admin skills API client in `frontend/services/api/admin/skills.ts`
- [X] T011 [US1] Build skills list page in `frontend/app/admin/skills/page.tsx`
- [X] T012 [US1] Build skill create/edit pages and form in `frontend/app/admin/skills/new/page.tsx`, `frontend/app/admin/skills/[skillId]/page.tsx`, and `frontend/components/admin/SkillForm.tsx`

**Checkpoint**: User Story 1 should be functional and independently usable

---

## Phase 4: User Story 2 - Manage scenarios and assign skills (Priority: P1)

**Goal**: Admins can create, edit, publish/unpublish, soft-delete/restore scenarios and assign ordered skills.

**Independent Test**: Create a scenario with skills, publish it, edit it, unpublish it, and verify validation and status rules.

### Tests for User Story 2 (write first)

- [X] T030 [P] [US2] Contract tests for admin scenarios API (CRUD, publish/unpublish, soft delete/restore, delete blocks) in `backend/tests/contract/test_admin_scenarios.py`
- [X] T031 [US2] Integration test for scenario validation (required fields, unique skills, publish/unpublish, delete blocked with sessions) in `backend/tests/integration/test_admin_scenarios_flow.py`
- [X] T032 [P] [US2] E2E test for admin scenarios UI (create/edit/publish/unpublish/delete/restore) in `frontend/tests/e2e/admin-scenarios.spec.ts`

### Implementation for User Story 2

- [X] T013 [P] [US2] Extend scenario repository for publish validation and soft delete/restore in `backend/app/repositories/admin_scenario_repository.py`
- [X] T014 [US2] Implement admin scenarios service (validation, concurrency, audit log) in `backend/app/services/admin/scenarios_service.py`
- [X] T015 [US2] Implement admin scenarios routes in `backend/app/api/routes/admin/scenarios.py`
- [X] T016 [P] [US2] Add admin scenarios API client in `frontend/services/api/admin/scenarios.ts`
- [X] T017 [US2] Build scenarios list page in `frontend/app/admin/scenarios/page.tsx`
- [X] T018 [US2] Build scenario create/edit pages and form in `frontend/app/admin/scenarios/new/page.tsx`, `frontend/app/admin/scenarios/[scenarioId]/page.tsx`, and `frontend/components/admin/ScenarioForm.tsx`

**Checkpoint**: User Stories 1 and 2 should both work independently

---

## Phase 5: User Story 3 - Review and maintain session data (Priority: P2)

**Goal**: Admins can list, inspect, and delete sessions with evaluation and transcript visibility.

**Independent Test**: Filter sessions, open a session detail view, and delete it with confirmation.

### Tests for User Story 3 (write first)

- [X] T033 [P] [US3] Contract tests for admin sessions API (list filters, detail, delete cascade) in `backend/tests/contract/test_admin_sessions.py`
- [X] T034 [US3] Integration test for session list/detail/delete with evaluation visibility in `backend/tests/integration/test_admin_sessions_flow.py`
- [X] T035 [P] [US3] E2E test for admin sessions UI (filter/detail/delete confirmation) in `frontend/tests/e2e/admin-sessions.spec.ts`

### Implementation for User Story 3

- [X] T019 [P] [US3] Implement admin sessions service (list/detail/delete, audit log) in `backend/app/services/admin/sessions_service.py`
- [X] T020 [US3] Implement admin sessions routes in `backend/app/api/routes/admin/sessions.py`
- [X] T021 [P] [US3] Add admin sessions API client in `frontend/services/api/admin/sessions.ts`
- [X] T022 [US3] Build sessions list page in `frontend/app/admin/sessions/page.tsx`
- [X] T023 [US3] Build session detail page with delete confirmation in `frontend/app/admin/sessions/[sessionId]/page.tsx`
- [X] T041 [US3] Show scenario title and formatted datetime in admin session list/detail via `backend/app/services/admin/sessions_service.py`, `frontend/app/admin/sessions/page.tsx`, and `frontend/app/admin/sessions/[sessionId]/page.tsx`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story improvements and admin audit log visibility

- [X] T024 [P] Expose audit log list endpoint in `backend/app/api/routes/admin/audit_log.py` and wire into `backend/app/api/routes/admin/router.py`
- [X] T025 [P] Build audit log list page in `frontend/app/admin/audit-log/page.tsx`
- [X] T026 [P] Update admin usage notes in `README.md`
- [X] T036 Wire audit logging into skills/scenarios/sessions services for create/update/delete in `backend/app/services/admin/*.py`
- [X] T037 Add admin API clients to send `X-Admin-Token` and `If-Match` headers for protected routes in `frontend/services/api/admin/*.ts`
- [X] T038 Add conflict handling (stale edits, delete blocks) UI feedback in admin forms/pages in `frontend/app/admin/**`
- [X] T039 Add measurement checks for SC-001..SC-004 (publish time, success rate, search speed, data quality) and document in `docs/` or `README.md`
- [X] T040 Extend CI/scripts to run new admin contract/integration/e2e suites in `scripts/` and pipeline configs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P1)**: Can start after Foundational (Phase 2)
- **User Story 3 (P2)**: Can start after Foundational (Phase 2)

### Parallel Execution Examples

- **US1**: `backend/app/repositories/skill_repository.py` and `frontend/services/api/admin/skills.ts`
- **US2**: `backend/app/repositories/scenario_repository.py` and `frontend/services/api/admin/scenarios.ts`
- **US3**: `backend/app/services/admin/sessions_service.py` and `frontend/services/api/admin/sessions.ts`

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate user story 1 via admin UI walkthrough

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Validate → Demo
3. Add User Story 2 → Validate → Demo
4. Add User Story 3 → Validate → Demo
5. Add Polish tasks as needed
