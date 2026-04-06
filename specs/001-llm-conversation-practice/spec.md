# Feature Specification: LLM Conversation Practice Coach

**Feature Branch**: `001-llm-conversation-practice`  
**Created**: 2025-12-06  
**Status**: Draft  
**Input**: User description: "This is an app that contains both backend API and frontend UI that leverages the power of LLM (both text and speech) to help people to practice communication skills in everyday scenarios. 
- Build a FastAPI/uvicorn/OpenAI AsyncClient backend plus frontend UI that lets trainees practice high-stakes conversations with an AI roleplayer powered by qwen3-omni-flash (speech + text).
- Scenarios are predefined by admins and include metadata (title, domain, etc.), context (situation, background, setting), simulation configuration (roles, dynamics, rules), and evaluation configuration.
- Practice flow: trainee selects a scenario, reviews context, and the conversation begins according to the simulation config (trainee or AI initiated); AI voices are generated via qwen3-omni-flash.
- After each practice, transcripts/audio feed a text-only LLM for scoring based on the scenario's evaluation criteria plus qualitative feedback; trainees can replay scenarios from history.
- All session data, including audio, is persisted via MongoDB and MinIO; no additional auth scope beyond the single-tenant stub user in this release.

## User Scenarios & Testing *(mandatory)*

Acceptance scenarios must be automatable and will drive TDD. Note any mocks/stubs required for
external systems to keep tests deterministic.

### User Story 1 - Practice a scenario with AI coach (Priority: P1)

The trainee selects a scenario, reviews its details, and completes a live conversation with the AI
roleplayer that ends when scenario criteria or timeout conditions are met.

**Why this priority**: Core value of the product; without practice flow, no user benefit.

**Independent Test**: Start a scenario, simulate audio/text turns with stubbed AI responses, and
verify the conversation ends correctly with transcripts and audio captured.

**Acceptance Scenarios**:

1. **Given** a published scenario with metadata, context, simulation and evaluation configurations, **When** the
   trainee starts the session, **Then** the conversation initiates as defined in the simulation config,
   and the browser plays AI audio responses where applicable.
2. **Given** an active session, **When** the trainee is silent for more than the allowed idle window or
   total duration exceeds the threshold, **Then** the session ends with the termination reason recorded
   and all turns saved.

---

### User Story 2 - Receive post-practice evaluation (Priority: P2)

After a session ends, the system compiles the conversation and sends it for evaluation, returning
ratings by skill and actionable feedback to the trainee.

**Why this priority**: Feedback loop is essential for learning and scenario replay.

**Independent Test**: Complete a recorded session, trigger evaluation via a stubbed text-only model,
verify ratings and feedback are produced and associated to the session.

**Acceptance Scenarios**:

1. **Given** a completed session with transcript and audio references, **When** the system requests
   evaluation, **Then** the trainee receives scores across the scenario's evaluation criteria and
   guidance on strengths and gaps.
2. **Given** an evaluation already exists, **When** the trainee views the session summary, **Then** the
   ratings and feedback are displayed without re-requesting the model.

---

### User Story 3 - Review and replay practice history (Priority: P3)

The trainee browses prior sessions, views details, and can start a new practice using any saved
scenario.

**Why this priority**: History enables tracking progress and reusing scenarios without re-entry.

**Independent Test**: With multiple saved sessions, list them, open one to see transcript/audio and
feedback, and start a new session from its scenario data.

**Acceptance Scenarios**:

1. **Given** saved sessions exist, **When** the trainee opens history, **Then** sessions are listed with
   scenario title, date, duration, and completion status.
2. **Given** a specific past session, **When** the trainee selects "practice again," **Then** a new
   session starts with the same scenario settings without altering the prior record.

---

### Edge Cases

- Silence longer than the idle threshold or exceeding maximum session duration ends the session with
  a clear termination reason.
- AI voice/text service unavailable or returns invalid output triggers a graceful stop with guidance
  to retry while preserving collected data.
- Uploaded audio is missing or corrupted; user is prompted to re-send the turn without corrupting the
  session record.
- End criteria met on the first exchange still yields a valid session with minimal transcript and
  stored metadata.
- Replaying a scenario from history creates a new session linked to the scenario without overwriting
  prior evaluations.

## Requirements *(mandatory)*

**Design Discipline**: Keep solutions simple (KISS, YAGNI, DRY, SOLID). Document rationale for any
complexity that remains.  
**Testing**: Requirements must be concrete enough to translate directly into automated tests written
before implementation, with mocks/stubs specified for any external services.

### Functional Requirements

- **FR-001**: System MUST provide a catalog of practice scenarios capturing metadata, context, simulation, and evaluation configurations.
- **FR-002**: Trainee MUST be able to start a practice session by selecting a scenario and reviewing its details before the AI initiates the first turn as defined in the simulation config.
- **FR-002a**: The practice room UI MUST play AI audio responses during live sessions, with a manual
  playback control when autoplay is blocked by the browser.
- **FR-003**: System MUST implement the Session Lifecycle Contract defined in Supporting Contracts (scenario validation, AI-first turn, timer handling, manual stops, per-turn simulation goal checks, and server-authoritative termination/push events).
- **FR-004**: System MUST capture every trainee/AI turn (transcript, speaker role, timestamps) and persist the associated audio reference exactly as described in the Audio & Media Contract, ensuring storage state always mirrors what was captured during the session.
- **FR-005**: Manual termination controls MUST remain available throughout the session per the Session Lifecycle Contract, and the server MUST record the trainee-selected reason.
- **FR-006**: Trainee turn handling MUST follow the Audio & Media Contract (audio + optional context input, immediate AI reply, asynchronous qwen ASR transcription, retries that preserve turn order).
- **FR-007**: Idle and total duration telemetry MUST be measured and reported by the client but validated/overridden by the server, matching the Session Lifecycle Contract.
- **FR-008**: Session start and per-turn timestamps MUST be included so the server can enforce the ≤2s drift rule in the Session Lifecycle Contract before issuing authoritative termination events; requests without timestamps fail fast with HTTP 422.
- **FR-009**: Per-turn simulation goal checks MUST use the simulation configuration, and the resulting decisions MUST trigger termination and WebSocket/poll notifications.
- Request: POST `{base}/chat/completions` with bearer auth and payload `{"model":GOAL_CHECK_MODEL,"messages":[{role:"system",content:"You assess whether the trainee achieved the goal..."},{role:"user",content:<structured transcript + simulation/evaluation configuration>}],"tools":[{"type":"function","function":{"name":"goal_check_result","parameters":{"type":"object","properties":{"status":{"type":"string","enum":["continue","succeeded","failed"]},"reason":{"type":"string"}},"required":["status"]}}}]}`. The backend supplies the latest transcript summary, scenario simulation and evaluation configurations, and server timestamps so the tool has full context.
- Response: the assistant MUST call the `goal_check_result` tool. `status="continue"` allows the session to proceed; `status="succeeded"` or `"failed"` causes immediate termination with `terminationReason=objective_met`/`objective_failed`. `reason` is persisted for observability.
- Persistence: when `status` is terminal, the backend records `objectiveStatus` plus `objectiveReason` on the PracticeSession (mirrored in API responses and logs) so clients can display why the model decided to stop.
- Testing guidance: provide a stub HTTP server that honors the tool schema so per-turn termination logic can be unit-tested; rejected/malformed responses are treated as `continue` and surfaced in logs.

#### Observability & Metrics Contract

- Emit structured logs for every session and turn capturing session ID, turn ID, latency, and termination reasons; logs feed troubleshooting and auditing.
- Publish metrics that align with success criteria SC-001 to SC-004: session completion rate, termination latency, evaluation turnaround, and ability to open history items within two steps (`historyStepCount` query parameter provided by clients on history list/detail API calls).
- Instrument OpenTelemetry-style traces covering request → AI call → storage so that latency hotspots are visible end-to-end.

## Assumptions & Dependencies

- Scenario library is curated and validated for completeness (nested configuration objects) before being published for practice.
- The Audio & Media Contract assumes qwen3-omni-flash (or a stub) can generate speech plus text each
  turn; testing environments provide safe fallbacks when the service is unavailable.
- The Evaluation Flow Contract assumes a text-only evaluator that consumes transcripts/audio metadata
  and produces structured rubric scores with notes.
- Default timer values (8-second idle, 5-minute total unless a scenario overrides) come from the
  Session Lifecycle Contract; clients measure locally while servers validate.
- Audio & Media Contract governs data retention (indefinite until deletion), codec/size rules, and storage.
- Asynchronous ASR + evaluation tasks ride on FastAPI background tasks (in-process asyncio); MVP
  scope accepts best-effort durability with manual requeue mechanisms if the API restarts mid-task.
- No authentication in this release; identity remains a single-tenant stub, and admin scenario seeding
  is handled out-of-band (no admin UI).
- Observability tooling follows the Observability & Metrics Contract (structured logs, metrics, traces).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of initiated sessions complete with a recorded termination reason and saved
  transcript/audio without system errors.
- **SC-002**: 95% of sessions meeting simulation end criteria or timeout stop within 2 seconds of detection and
  persist the final state.
- **SC-003**: 90% of evaluations deliver ratings and feedback to the trainee within 60 seconds of
  session completion (reflects async FastAPI background tasks + retries).
- **SC-004**: 95% of trainees can locate and open a past session with transcript and feedback in under
  two navigation steps from the history list. A “step” equals a top-level navigation action initiated
  on the history list (first click selects a session, second click opens detail). Clients MUST include
  a `historyStepCount` query parameter when calling history list/detail APIs; the backend rejects
  requests without it and uses the provided hint to emit SC-004 metrics.

## Clarifications

### Session 2025-12-06
- Q: How long should transcripts and audio be retained? → A: Audio & Media Contract: retain until the trainee deletes the session.
- Q: How is user speech turned into text for turns? → A: Audio & Media Contract: trainee sends audio + optional context, backend triggers immediate AI reply and asynchronous qwen ASR transcription.
- Q: What audio format/flow and fallback should be used? → A: Audio & Media Contract: base64 MP3 per turn (<128 KB, mono ≤24 kbps) with retries that preserve prior turns.
- Q: How should evaluations score communication skills? → A: Evaluation Flow Contract: numeric 1–5 rubric with per-skill notes plus overall summary.
- Q: Where are idle/timeout timers measured? → A: Session Lifecycle Contract: client measures and reports, server recalculates and is authoritative.
- Q: How is audio stored and where? → A: Audio & Media Contract: media storage with only references stored in records.
- Q: How should history listing paginate/sort/filter/search? → A: Page size 20, newest-first; filter by scenario and category.
- Q: What is the auth scope/roles for this release? → A: No auth (public); identity stubbed; scenario seeding out-of-band; admin UI deferred.
- Q: What observability signals are required? → A: Observability & Metrics Contract: structured logs, metrics mapped to SC-001–SC-004, and traces across request → AI call → storage.
- Q: What rate limiting applies? → A: None for this release.
- Q: Any accessibility/localization requirements? → A: None specified for this release.
- Q: What per-turn audio size cap/encryption applies? → A: Audio & Media Contract: single-turn MP3 must stay under the 128 KB limit; HTTPS covers transit.
- Q: What is the qwen3-omni-flash API contract? → A: Audio & Media Contract: bearer auth JSON calls that include persona/system text + MP3 input and return MP3 + transcript with 10s timeout and two retries on 5xx/timeouts.
- Q: How are client timers validated? → A: Session Lifecycle Contract: client sends start/per-turn timestamps; server recalculates, tolerates ≤2s drift, otherwise overrides.
- Q: Do we store raw base64 in session records? → A: Audio & Media Contract: only references/metadata live in records.
- Q: Is evaluation synchronous or async? → A: Evaluation Flow Contract: async FastAPI background tasks with status + retry (best effort), results polled until ready.
- Q: How do deletes work? → A: Audio & Media Contract + FR-016: hard delete session/evaluation records and cascade to storage files; no soft delete.
- Q: What are the session end conditions? → A: Session Lifecycle Contract: manual stop, client close, timer breach, or text-only simulation goal check deciding success/failure.
- Q: Are during-session and post-session models tied to qwen3-omni-flash? → A: Session Lifecycle + Evaluation Flow Contracts: both simulation goal checks and post-session evaluations use configurable text-only models (not the speech model).
- Q: How are qwen generation calls authenticated and formatted? → A: Use the DashScope OpenAI Python AsyncClient (≥1.52.0) with `stream=True`, `modalities=["text","audio"]`, and `audio={"voice": "...", "format": "wav"}`. The AsyncClient handles SSE streaming automatically and accumulates text and audio chunks. **Implementation Note**: Qwen returns raw PCM audio (not WAV). The backend detects audio format by checking for "RIFF" header and converts raw PCM to MP3 using ffmpeg with `-f s16le -ar 24000 -ac 1` flags, then stores references only.
- Q: Which text-only evaluator backs post-session scoring? → A: GPT-5 mini served at `https://api.chataiapi.com/v1/chat/completions`, authenticated via bearer `secretKey` using OpenAI-style chat payloads; the assistant response provides rubric scores/notes that we persist.
- Q: How do ASR and generation calls differ? → A: Audio & Media Contract: generation returns audio+transcript synchronously; ASR is an async audio-only call that feeds trainee transcripts without blocking the AI reply.
- Q: How are termination signals transported? → A: Session Lifecycle Contract: server pushes WebSocket termination events with poll fallback and authoritative decision.
- Q: How is async evaluation executed? → A: Evaluation Flow Contract: FastAPI background tasks mark records and retry with backoff while the API remains available; manual requeue is exposed for additional attempts.
- Q: How do we fit 128 KB audio? → A: Audio & Media Contract: enforce mono ≤24 kbps MP3 (~5–6s), provide UX warnings before exceeding the cap, and fail fast on oversized uploads.
- Q: How is identity handled in single-tenant mode? → A: Use a fixed stub user ID to scope sessions/history/deletes and avoid cross-user leakage.
- Q: Where to emit observability data? → A: Observability & Metrics Contract: OpenTelemetry-style spans + logging with session/turn IDs, latencies, termination reasons, and metrics tied to SC-001–SC-004.
- Q: Do we ever store raw base64 outside the media storage? → A: Audio & Media Contract: raw audio stays in-memory for upload/ASR; only references + transcripts reach persistent storage.
- Q: Who is the termination authority? → A: Session Lifecycle Contract: server decides and pushes termination events; client reports telemetry only.
- Q: What concurrent session load should the system target? → A: Size for fewer than 20 simultaneous sessions (single-team pilot scale).
- Q: What concurrent session load should the system target? → A: Size for fewer than 20 simultaneous sessions (single-team pilot scale).
