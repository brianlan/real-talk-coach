# Implementation Plan: LLM Conversation Practice Coach

**Branch**: `001-llm-conversation-practice` | **Date**: 2025-12-07 | **Spec**: `specs/001-llm-conversation-practice/spec.md`
**Input**: Feature specification from `/specs/001-llm-conversation-practice/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Constitution gates below must
be satisfied before moving forward.

## Summary

Deliver a FastAPI/Uvicorn/httpx backend plus a web UI that lets trainees run voiced conversations
against qwen3-omni-flash roleplayers, persist audio/transcripts/evaluations in LeanCloud, and surface
history/replay plus async rubric scoring. Architecture centers on an async FastAPI service with
server-authoritative timers/WebSockets, a Next.js 15 frontend that streams audio and listens for
termination/evaluation events, and LeanCloud REST models for Scenario, PracticeSession, Turn, and
Evaluation. Asynchronous evaluation + ASR work is handled via FastAPI background tasks (best-effort
durability) so we can ship the MVP without provisioning separate worker infrastructure. Research
validated LeanCloud access patterns, qwen retry envelopes, and the <20-session pilot capacity
assumption to size infra and background task load.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Backend Python 3.11 (FastAPI); Frontend TypeScript/Next.js 15  
**Primary Dependencies**: FastAPI, Uvicorn, httpx, WebSockets, LeanCloud REST APIs, qwen3-omni-flash, OpenAI Python SDK (DashScope compatible), GPT-5 mini text-only API (https://api.chataiapi.com), Next.js/React, Web Audio API  
**Storage**: LeanCloud LObject/LFile for structured data + audio references  
**Testing**: Pytest + httpx AsyncClient, pytest-asyncio for backend; Vitest + Testing Library + Playwright for frontend/e2e  
**Target Platform**: Backend: Linux containers (uvicorn workers); Frontend: modern evergreen browsers  
**Project Type**: Full-stack web (separate backend + frontend packages)  
**Performance Goals**: Termination events dispatched <=2s after condition; evaluations within 60s p90; client latency budget <500ms for turn ACKs  
**Constraints**: Mono MP3 <128 KB per turn, qwen request timeout 10s with 2 retries, timer drift <=2s, graceful degradation above 20 sessions  
**Scale/Scope**: Pilot of <20 concurrent sessions, dozens of predefined scenarios, single-tenant stub user

## Constitution Check (Pre-Design)

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Readability & Explicitness: Documenting backend/frontend responsibilities and contracts up front
  keeps flows explicit; no hidden service discovery.
- TDD-First & Isolated: Pytest/Vitest harnesses will stub qwen + LeanCloud via httpx/Mock Service
  Worker to keep loops deterministic.
- Automation Everywhere: Formatting (ruff/black/eslint/prettier) and test commands will be scripted
  in the quickstart plus CI pipeline gates.
- Simple, Disciplined Design: Single FastAPI app + Next.js client avoids premature microservices; we
  reuse LeanCloud directly per KISS/YAGNI.
- Purposeful Comments & Rationale: Plan + contracts capture "why" for timers, retries, and deletion
  cascades so code comments can stay concise.

**Gate Status**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

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

**Structure Decision**: Use discrete `backend/` and `frontend/` workspaces so API/background-task code
and UI assets remain isolated yet share the same repo; mirrors hosting split (FastAPI service + static
web bundle) and keeps tests scoped per surface.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None_ | – | – |

## Phase 0 – Outline & Research

**Inputs captured from Technical Context**
- Dependencies: FastAPI, Uvicorn, httpx, WebSockets, Next.js/React, Web Audio API, LeanCloud REST,
  qwen3-omni-flash.
- Integrations: LeanCloud LObject/LFile storage, qwen speech+ASR, text-only evaluator LLM,
  WebSocket termination/polling channels.

**Research tasks dispatched**
- Best practices for running FastAPI + WebSockets with in-process background tasks under <20-session load.
- Patterns for storing conversational turns + audio references in LeanCloud via REST with cascade delete.
- Evaluate frontend framework tradeoffs for audio capture + streaming (Next.js vs Vite SPA).
- Durable evaluation/ASR background-task design with retries/backoff (ensuring best effort without dedicated workers).

**Output**: `specs/001-llm-conversation-practice/research.md`

Key findings:
1. Stay with FastAPI + async stack because it satisfies concurrency + WebSocket requirements while
   remaining lightweight.
2. Treat LeanCloud as the sole persisted store (LObject/LFile) to honor contracts and avoid secret
   leakage to frontend.
3. Choose Next.js 15 (App Router) for SSR history views and ergonomic integration with Web Audio/WebSocket.
4. Use FastAPI background tasks/asyncio to run evaluation + ASR flows without separate worker infra,
   accepting MVP-level durability in exchange for reduced ops overhead.

All Technical Context unknowns resolved (none remaining marked as NEEDS CLARIFICATION).

## Phase 1 – Design & Contracts

**Artifacts produced**
- `specs/001-llm-conversation-practice/data-model.md`: Scenario, PracticeSession, Turn, Evaluation
  schemas + states and observability expectations.
- `specs/001-llm-conversation-practice/contracts/openapi.yaml`: REST surface for scenarios, sessions,
  turns, manual stop, deletion, and evaluation status/retry.
- `specs/001-llm-conversation-practice/quickstart.md`: Install/prereqs, env vars, run/test commands,
  mocking story, and deployment notes.
- Agent context updated via `.specify/scripts/bash/update-agent-context.sh codex`, producing
  `/home/rlan/projects/real-talk-coach/AGENTS.md`.

**Design highlights**
- Server authoritative session lifecycle with `PracticeSession.status` transitions and WebSocket
  channel per session ensures timers + termination reasons stay consistent; WebSocket message schema
  (`ai_turn`, `termination`, `evaluation_ready`) mirrors the REST Turn/Evaluation payloads.
- Turn storage enforces LeanCloud sequence uniqueness and 128 KB MP3 constraints while capturing ASR
  status so UI can show pending transcripts.
- Client-provided timing data is formalized: `/api/sessions` accepts `clientSessionStartedAt`, and
  every trainee turn includes `startedAt/endedAt` so the backend can compute drift and idle/total duration.
- Turn handling module wraps the OpenAI-compatible qwen SDK (`stream=True`, `modalities=["text","audio"]`,
  `audio={"voice": …, "format": "wav"}`), decodes streamed WAV chunks, transcodes them to mono ≤24 kbps
  MP3, and persists LeanCloud references alongside transcripts.
- Evaluation API exposes cached results plus a safe requeue endpoint; FastAPI background tasks pick
  up pending evaluations/ASR work, handle retries while the process stays alive, and update LeanCloud.
  Evaluations call GPT-5 mini via `https://api.chataiapi.com/v1/chat/completions` with bearer secrets
  and OpenAI-style chat payloads, then map the assistant response to rubric scores/notes.
- Quickstart enumerates automation commands so CI can mirror: `ruff`, `pytest`, `pnpm lint/test`,
  `pnpm playwright test`.

## Phase 2 – Implementation Plan (Preview)

Will break into incremental stories during `/speckit.tasks`, roughly:
1. **Backend foundations**: scaffold FastAPI project, env loading, LeanCloud + qwen clients, health
   + observability plumbing, pytest fixtures/mocks.
2. **Session lifecycle**: scenario catalog endpoints, session start/manual stop/delete, WebSocket hub,
   idle/duration enforcement, LeanCloud persistence + cascading deletes.
3. **Turn handling & media**: audio upload pipeline to LeanCloud, qwen generation via OpenAI SDK
   (streaming text+WAV audio) with WebSocket push plumbing, WAV→MP3 transcode, qwen ASR integration,
   retries + telemetry, history listing.
4. **Evaluation & ASR tasks**: FastAPI background task orchestration, enqueue markers in LeanCloud,
   GPT-5 mini (chataiapi.com) client wrapper, state transitions, HTTP evaluation status endpoint,
   requeue hook, instrumentation.
5. **Frontend**: Next.js app scaffolding, scenario browser, practice room with audio capture + stream,
   history/evaluation screens, WebSocket termination handling.
6. **Testing/automation**: contract tests against OpenAPI, MSW mocks, Playwright happy-path practice
   + history flows, CI wiring.

## Constitution Check (Post-Design)

- Readability & Explicitness: Data model + OpenAPI keep flows explicit; plan documents rationale for
  FastAPI background task usage, qwen, LeanCloud.
- TDD-First & Isolated: Quickstart + plan lock in pytest/Vitest/Playwright loops with mocked qwen +
  LeanCloud so red-green remains practical.
- Automation Everywhere: Quickstart enumerates lint/test commands for CI parity; future tasks will
  codify them in scripts.
- Simple, Disciplined Design: One backend + one frontend; all async work stays inside FastAPI
  background tasks so we avoid extra services.
- Purposeful Comments & Rationale: Research + plan capture necessary tradeoffs (Next.js vs Vite,
  background tasks vs dedicated workers), so implementation can reference them.

**Gate Status**: PASS
