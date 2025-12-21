# Tasks: LLM Conversation Practice Coach

**Input**: Design documents from `/specs/001-llm-conversation-practice/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED by the constitution. Write them first (failing), use mocks/stubs for
external services, and keep them automated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish environment scaffolding and developer workflows before feature work begins.

- [X] T001 Create `backend/.env.example` capturing LeanCloud, DashScope/qwen, evaluator, and stub user variables from quickstart.md.
- [X] T002 Create `frontend/.env.local.example` with `NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_WS_BASE` placeholders for local/dev/prod targets.
- [X] T003 Update `README.md` with backend/frontend install, run, and test commands mirroring `specs/001-llm-conversation-practice/quickstart.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure (app scaffolding, config, shared clients, telemetry, test fixtures) required by every user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004a [P] Author pytest unit/contract tests that pin FastAPI lifespan hooks, router mounts, and default CORS behavior in `backend/tests/unit/test_main.py` before any `backend/app/main.py` code exists.
- [X] T004 Scaffold FastAPI entrypoint with lifespan hooks, router mounts, and CORS defaults in `backend/app/main.py` per plan structure.
- [X] T005a [P] Write tests in `backend/tests/unit/test_config.py` verifying the settings loader rejects missing/invalid env vars with actionable errors.
- [X] T005 [P] Implement strongly typed settings loader with env validation in `backend/app/config.py` for LeanCloud/qwen/evaluator/objective-check secrets.
- [X] T006a [P] Create MockTransport-backed tests in `backend/tests/unit/test_leancloud_client.py` asserting retries, signed URL helpers, and error surfacing for the LeanCloud client.
- [X] T006 [P] Create LeanCloud REST client with httpx session pooling, retries, and signed file helpers in `backend/app/clients/leancloud.py`.
- [X] T007a [P] Add tests in `backend/tests/unit/test_llm_clients.py` covering qwen (generation + ASR) and GPT-5 mini wrapper timeouts, retries, and JSON contracts.
- [X] T007 [P] Build qwen (generation+ASR) and GPT-5 mini evaluation client wrappers with timeout/retry policies in `backend/app/clients/llm.py`.
- [X] T008a [P] Write telemetry helper tests in `backend/tests/unit/test_tracing.py` ensuring structured logs/metrics emit sessionId/turnId and SC-00x attributes.
- [X] T008 [P] Add structured logging + OpenTelemetry helpers in `backend/app/telemetry/tracing.py` for session/turn metrics.
- [X] T009 Establish pytest fixtures + httpx MockTransport stubs for LeanCloud/qwen/evaluator in `backend/tests/conftest.py`.
- [X] T010 Implement deterministic scenario/skill importer script `scripts/seed_scenarios.py` that honors `seed-data/*.json` contracts.
- [ ] T011 [P] Create shared frontend providers (QueryClient, WebSocket context, global styles) in `frontend/app/layout.tsx` and `frontend/app/providers/app-providers.tsx`.

---

## Phase 3: User Story 1 - Practice a scenario with AI coach (Priority: P1) 🎯 MVP

**Goal**: Enable trainees to browse published scenarios, start a practice session, exchange audio turns with the AI roleplayer, and end sessions per lifecycle contract.

**Independent Test**: Start a scenario, simulate alternating turns via stubs, and verify transcripts/audio + termination reason persist.

### Tests for User Story 1 ⚠️

- [ ] T012 [P] [US1] Add contract tests for `GET /api/scenarios*`, `GET /api/skills`, `POST /api/sessions`, and `POST /api/sessions/{sessionId}/turns` in `backend/tests/contract/test_sessions.py` and `backend/tests/contract/test_turns.py` using MockTransport.
- [ ] T012a [P] [US1] Add contract test in `backend/tests/contract/test_turns.py` proving audio payloads >128 KB receive HTTP 413 with actionable guidance.
- [ ] T013 [P] [US1] Implement integration test covering trainee turn upload → AI reply → termination (idle + manual stop) in `backend/tests/integration/test_practice_flow.py`.
- [ ] T014 [P] [US1] Create Playwright happy-path test for selecting a scenario and completing a conversation in `frontend/tests/e2e/practice.spec.ts` with mocked WebSocket events.
- [ ] T015 [P] [US1] Add contract test that rejects POST `/api/sessions` when personas/objectives/endCriteria are incomplete in `backend/tests/contract/test_sessions.py` (expects HTTP 422 with actionable errors).
- [ ] T016 [P] [US1] Extend integration coverage to simulate objective-check succeed/fail outcomes via stubbed responses in `backend/tests/integration/test_practice_flow.py`.
- [ ] T016a [P] [US1] Add integration test in `backend/tests/integration/test_practice_flow.py` simulating qwen generation/ASR outages to ensure sessions terminate gracefully with retry messaging.
- [ ] T016b [P] [US1] Extend integration coverage to assert session completion enqueues an evaluation job by mocking `evaluation_runner.enqueue` inside `backend/tests/integration/test_practice_flow.py`.

### Implementation for User Story 1

- [ ] T017 [P] [US1] Implement LeanCloud repositories for Scenario, Skill, PracticeSession, and Turn classes in `backend/app/repositories/scenario_repository.py` and `backend/app/repositories/session_repository.py`.
- [ ] T018 [P] [US1] Expose scenario + skill catalog APIs per OpenAPI contract in `backend/app/api/routes/scenarios.py` including search/filter logic.
- [ ] T019 [US1] Model PracticeSession/Turn schemas and validators enforcing timestamps + drift in `backend/app/models/session.py`.
- [ ] T020 [US1] Build `/api/sessions` REST routes (list/create/detail/delete/manual-stop) in `backend/app/api/routes/sessions.py` with LeanCloud persistence + cascade hooks.
- [ ] T021 [US1] Implement `POST /api/sessions/{sessionId}/turns` in `backend/app/api/routes/turns.py` validating session state, sequence, timestamps, and delegating to the turn pipeline service.
- [ ] T021a [US1] Enforce MP3 size/bitrate validation in `backend/app/api/routes/turns.py`, returning HTTP 413 with actionable errors when payloads exceed LeanCloud limits.
- [ ] T022 [US1] Implement per-session WebSocket hub with `ai_turn`, `termination`, `evaluation_ready` events in `backend/app/api/routes/session_socket.py`.
- [ ] T023 [US1] Create turn pipeline orchestrator (upload audio → qwen generation → LeanCloud storage) with ASR background task handling in `backend/app/services/turn_pipeline.py`.
- [ ] T023a [US1] Extend `backend/app/services/turn_pipeline.py` to detect qwen generation/ASR failures, persist termination reasons, emit guidance over WebSocket, and notify observability sinks.
- [ ] T023b [US1] Add missing/corrupt audio recovery in `backend/app/services/turn_pipeline.py`, preserving turn order, prompting clients to resend, and ensuring retries don’t corrupt session state.
- [ ] T024 [US1] Integrate Configurable Objective Check Model client and termination enforcement in `backend/app/services/objective_check.py`.
- [ ] T024a [US1] Invoke `backend/app/tasks/evaluation_runner.enqueue()` whenever a session transitions to a terminal state in `backend/app/services/session_service.py`, ensuring idempotency and log coverage.
- [ ] T025 [US1] Persist manual stop reasons + timer breaches via service hooks in `backend/app/services/session_service.py` to satisfy FR-003/FR-005/FR-007.
- [ ] T025a [US1] Enforce the `<20` concurrent session cap with ≤5 pending queue plus HTTP 429 “pilot capacity exceeded” responses in `backend/app/services/session_service.py`, including contract/integration tests for saturation.
- [ ] T025b [P] [US1] Emit saturation metrics/alerts (SC-001/SC-004 linkage) and document the graceful degradation runbook in `backend/app/telemetry/tracing.py` and `docs/architecture/practice-coach.md`.
- [ ] T026 [US1] Enforce session/turn timestamp validation (startedAt/endedAt required, drift +/-2s) with HTTP 422 responses in `backend/app/api/routes/sessions.py` and `backend/app/api/routes/turns.py`.
- [ ] T027 [US1] Add contract tests for timestamp validation/drift enforcement (missing timestamps → 422) in `backend/tests/contract/test_sessions.py` and `backend/tests/contract/test_turns.py`.
- [ ] T027a [US1] Add contract test in `backend/tests/contract/test_turns.py` verifying missing/corrupt audio uploads trigger HTTP 422 with “resend turn” guidance while preserving session data.
- [ ] T028 [US1] Inject `STUB_USER_ID` scoping for all practice/evaluation/history queries in `backend/app/api/routes/` to uphold the single-tenant requirement.
- [ ] T029 [US1] Instrument session lifecycle + turn pipeline with structured logs and metrics covering SC-001 (completion rate) and SC-002 (termination latency), including unit tests that assert emission hooks via `backend/app/telemetry/tracing.py`.
- [ ] T030 [US1] Implement OpenTelemetry traces across `/api/sessions`, `backend/app/services/turn_pipeline.py`, and `backend/app/clients/*` so request → qwen → LeanCloud spans are emitted; add tests asserting span metadata (sessionId, turnId, latency).
- [ ] T031 [US1] Trigger AI initiation turn (sequence 0) immediately after session creation in `backend/app/services/session_service.py`, persist the AI turn, and ensure it streams over `/ws/sessions/{id}` before trainee input.
- [ ] T032 [P] [US1] Extend integration tests in `backend/tests/integration/test_practice_flow.py` to verify AI turn 0 is emitted after POST `/api/sessions` succeeds.
- [ ] T033 [P] [US1] Build scenario catalog page with filters/search in `frontend/app/(dashboard)/scenarios/page.tsx` consuming `/api/scenarios` + `/api/skills`.
- [ ] T034 [P] [US1] Implement scenario detail view + session start CTA in `frontend/app/(dashboard)/scenarios/[scenarioId]/page.tsx` calling `/api/sessions`.
- [ ] T035 [US1] Create practice room UI with WebSocket turn stream, manual stop controls, and termination banners in `frontend/app/practice/[sessionId]/page.tsx`.
- [ ] T035a [US1] Surface explicit qwen outage states in `frontend/app/practice/[sessionId]/page.tsx`, including retry CTA and preserved transcript context.
- [ ] T036 [P] [US1] Implement reusable audio capture + MP3 encoding hook in `frontend/services/audio/useAudioRecorder.ts` enforcing 128 KB limit guidance.
- [ ] T036a [P] [US1] Enhance `frontend/services/audio/useAudioRecorder.ts` and `frontend/services/api/sessions.ts` so “resend audio” responses replay the failed turn without duplicating state.
- [ ] T037 [P] [US1] Add API/WebSocket clients for sessions/turns in `frontend/services/api/sessions.ts` with idle/timeout telemetry submission.

**Checkpoint**: User Story 1 delivers the conversational MVP end-to-end.

---

## Phase 4: User Story 2 - Receive post-practice evaluation (Priority: P2)

**Goal**: After a session ends, compile transcripts/audio metadata, run GPT-5 mini evaluation, and expose ratings/feedback to the trainee with requeue controls.

**Independent Test**: Complete a session, trigger evaluation via stubbed model, and assert ratings + summary persist and display without duplicate runs.

### Tests for User Story 2 ⚠️

- [ ] T038 [P] [US2] Write contract tests for `GET/POST /api/sessions/{id}/evaluation` in `backend/tests/contract/test_evaluations.py` validating status transitions.
- [ ] T039 [P] [US2] Add integration test that simulates session completion and background evaluation retries in `backend/tests/integration/test_evaluation_flow.py`.
- [ ] T040 [P] [US2] Add frontend component/unit test ensuring evaluation results render + requeue disabled states in `frontend/tests/unit/evaluation-panel.test.tsx`.

### Implementation for User Story 2

- [ ] T041 [P] [US2] Extend LeanCloud models + repositories for Evaluation records in `backend/app/models/evaluation.py` and `backend/app/repositories/evaluation_repository.py`.
- [ ] T042 [US2] Implement FastAPI background task runner for evaluator calls with backoff + state updates in `backend/app/tasks/evaluation_runner.py`.
- [ ] T043 [US2] Create evaluation API routes (status fetch + requeue) in `backend/app/api/routes/evaluations.py` reusing LeanCloud repository + concurrency guards.
- [ ] T044 [US2] Wire GPT-5 mini prompt/response parsing + observability in `backend/app/services/evaluation_service.py`.
- [ ] T045 [P] [US2] Build frontend evaluation panel component in `frontend/components/session/EvaluationPanel.tsx` showing per-skill ratings + notes.
- [ ] T046 [US2] Implement polling/requeue hooks for evaluations in `frontend/services/api/evaluationClient.ts` and integrate with practice/history views.
- [ ] T047 [US2] Instrument evaluation runner + API responses with structured logs and metrics for SC-003 (queue-to-complete latency) plus verification tests in `backend/app/tasks/evaluation_runner.py` and `backend/app/api/routes/evaluations.py`.
- [ ] T048 [US2] Add OpenTelemetry spans around evaluation background tasks and LeanCloud writes in `backend/app/tasks/evaluation_runner.py` and `backend/app/services/evaluation_service.py`, with tests verifying span attributes (sessionId, status, latency).

**Checkpoint**: Evaluations run asynchronously, expose progress, and display actionable feedback.

---

## Phase 5: User Story 3 - Review and replay practice history (Priority: P3)

**Goal**: Let trainees browse historical sessions, inspect transcripts/audio/evaluations, delete records, and start new sessions from saved scenarios.

**Independent Test**: Populate multiple sessions, list/filter them, open a detail view with transcripts/evaluation, and launch a "practice again" flow without overwriting originals.

### Tests for User Story 3 ⚠️

- [ ] T049 [P] [US3] Add contract tests for session history pagination/filtering, delete cascade, default `sort=startedAtDesc`, optional `sort=startedAtAsc`, page size 20, title/objective substring search, and the required `historyStepCount` query parameter in `backend/tests/contract/test_history.py`.
- [ ] T050 [P] [US3] Implement integration test covering history detail fetch + practice-again handoff, ensuring `historyStepCount` hints propagate to metrics, in `backend/tests/integration/test_history_replay.py`.
- [ ] T051 [P] [US3] Add Playwright test for browsing history and replaying a session in `frontend/tests/e2e/history.spec.ts`.

### Implementation for User Story 3

- [ ] T052 [P] [US3] Implement history list query with filters/search/sort in `backend/app/api/routes/history.py`, requiring the `historyStepCount` query parameter (HTTP 422 if missing) and emitting SC-004 metrics (history access latency/two-step success) alongside the `SessionPage` responses.
- [ ] T053 [P] [US3] Generate short-lived signed LeanCloud audio URLs (TTL 15 minutes) when serving history detail responses in `backend/app/api/routes/history.py`, documenting retry/error semantics and requiring the `historyStepCount` hint for SC-004 metrics.
- [ ] T054 [P] [US3] Instrument history list/detail endpoints and practice-again flow with traces covering REST handlers and LeanCloud lookups in `backend/app/api/routes/history.py` and `backend/app/api/routes/sessions.py`, plus tests confirming span metadata (historyPage, sort/filter params).
- [ ] T055 [US3] Create session deletion + LeanCloud cascade orchestrator in `backend/app/services/session_cleanup.py` for DELETE `/api/sessions/{id}`.
- [ ] T056 [US3] Add "practice again" helper that clones scenario metadata and reuses POST `/api/sessions` to start new runs in `backend/app/api/routes/sessions.py`.
- [ ] T057 [P] [US3] Build history list UI with filters/search in `frontend/app/(dashboard)/history/page.tsx`, sending the required `historyStepCount` query parameter with API calls.
- [ ] T058 [US3] Implement session detail view (transcripts, audio playback via signed URLs, evaluation) in `frontend/app/(dashboard)/history/[sessionId]/page.tsx`, handling signed URL expiry/retry UX and transmitting `historyStepCount` hints.
- [ ] T059 [US3] Add reusable "Practice Again" CTA component in `frontend/components/history/PracticeAgainButton.tsx` to invoke `/api/sessions` with prior scenario data.

**Checkpoint**: Trainees can review and replay sessions independently from evaluations.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, resiliency hardening, and regression coverage once core stories are complete.

- [ ] T060 [P] Document architecture decisions, API surface, and background task flows in `docs/architecture/practice-coach.md`.
- [ ] T061 [P] Add objective-check + timer drift unit/regression coverage in `backend/tests/unit/test_objective_check.py`.
- [ ] T062 Run end-to-end quickstart validation script covering lint/test/playwright in `scripts/ci/validate-feature.sh` and update CI docs if needed.

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → prerequisite for Foundational.
- **Foundational (Phase 2)** → must be 100% complete before any user story; establishes config, clients, fixtures, and UI scaffolding.
- **User Story Order**: US1 (P1) → US2 (P2) → US3 (P3). Each depends on Foundational but can run in parallel after their predecessors if shared contracts are respected. US2 requires session lifecycle hooks from US1; US3 depends on session persistence from US1 and evaluation linkage from US2.
- **Polish** starts only after all targeted stories are code-complete + tested.

## Parallel Execution Examples

- **US1**: T012–T016 tests can run concurrently; T033 and T034 (distinct Next.js pages) can proceed while backend turn pipeline (T023) is in flight.
- **US2**: T038 and T039 execute in parallel, while T045 (frontend panel) can build against mocked API responses independent of backend T042.
- **US3**: T049–T051 tests run simultaneously; frontend history UI tasks (T057/T058) can proceed in parallel with backend history API (T052).

## Implementation Strategy

1. **MVP First**: Deliver Setup → Foundational → US1 to unblock live practice flow; validate via integration + Playwright tests before adding evaluations/history.
2. **Incremental Delivery**: Layer US2 (evaluations) next, ensuring async background tasks and polling integrate cleanly without blocking US1 endpoints.
3. **Parallelization**: After Foundational, dedicate separate owners per story (e.g., backend focus on T020–T028 while frontend handles T033–T037) and keep [P] tasks aligned to avoid file conflicts.
4. **Polish Last**: Once US1–US3 pass acceptance tests, complete docs, add regression coverage, and run full quickstart validation to prep for release.
