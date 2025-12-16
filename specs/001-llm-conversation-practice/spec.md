# Feature Specification: LLM Conversation Practice Coach

**Feature Branch**: `001-llm-conversation-practice`  
**Created**: 2025-12-06  
**Status**: Draft  
**Input**: User description: "This is an app that contains both backend API and frontend UI that leverages the power of LLM (both text and speech) to help people to practice communication skills in everyday scenarios. 
- Build a FastAPI/uvicorn/httpx backend plus frontend UI that lets trainees practice high-stakes conversations with an AI roleplayer powered by qwen3-omni-flash (speech + text).
- Scenarios are predefined by admins and include category, title, description, objectives, personas/backgrounds for both parties, and explicit end criteria.
- Practice flow: trainee selects a scenario, reviews context, AI initiates, turns alternate until objective met, timeout reached, or trainee stops; AI voices are generated via qwen3-omni-flash.
- After each practice, transcripts/audio feed a text-only LLM for skill ratings (1–5) plus qualitative feedback; trainees can replay scenarios from history.
- All session data, including LeanCloud LFiles that hold audio, is persisted via LeanCloud REST APIs; no additional auth scope beyond the single-tenant stub user in this release."


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

1. **Given** a published scenario with category, objective, personas, and end criteria, **When** the
   trainee starts the session, **Then** the AI initiates the conversation in the specified persona and
   presents the scenario context.
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
   evaluation, **Then** the trainee receives ratings across relevant communication skills and
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

- **FR-001**: System MUST provide a catalog of practice scenarios capturing category, title, description, objective, participant backgrounds/personas, and explicit end criteria.
- **FR-002**: Trainee MUST be able to start a practice session by selecting a scenario and reviewing its details before the AI initiates the first turn in the specified persona.
- **FR-003**: System MUST implement the Session Lifecycle Contract defined in Supporting Contracts (scenario validation, AI-first turn, timer handling, manual stops, per-turn objective checks, and server-authoritative termination/push events).
- **FR-004**: System MUST capture and persist each turn's transcript and associated audio reference (LeanCloud LFile) with timestamps and speaker roles, exactly as described in the Audio & Media Contract.
- **FR-005**: Manual termination controls MUST remain available throughout the session per the Session Lifecycle Contract, and the server MUST record the trainee-selected reason.
- **FR-006**: Trainee turn handling MUST follow the Audio & Media Contract (audio + optional context input, immediate AI reply, asynchronous qwen ASR transcription, retries that preserve turn order).
- **FR-007**: Idle and total duration telemetry MUST be measured and reported by the client but validated/overridden by the server, matching the Session Lifecycle Contract.
- **FR-008**: Session start and per-turn timestamps MUST be included so the server can enforce the ≤2s drift rule in the Session Lifecycle Contract before issuing authoritative termination events.
- **FR-009**: Per-turn objective checks MUST use the configurable text-only model in the Session Lifecycle Contract, and the resulting decisions MUST trigger termination and WebSocket/poll notifications.
- **FR-010**: Scenarios and session/evaluation records MUST be stored in LeanCloud using LObject; audio blobs stored as LeanCloud LFile with access via LeanCloud REST over HTTPS.
- **FR-011**: System operates without authentication; practice/history/evaluation endpoints assume a single-tenant, stubbed user ID to scope sessions/history/deletes; admin scenario management is out-of-band (no admin UI).
- **FR-012**: Observability MUST follow the Observability & Metrics Contract (structured logs with session/turn IDs + latencies, metrics mapped to SC-001–SC-004, and traces across request → AI call → storage).
- **FR-013**: Codec, size limits, storage method, encryption, and retries MUST comply with the Audio & Media Contract.
- **FR-014**: Turn records MUST persist audio references and transcripts in the manner specified by the Audio & Media Contract (AI transcript from generation response, trainee transcript from async ASR, no raw base64 duplication).
- **FR-015**: All qwen3-omni-flash interactions (generation + ASR) MUST satisfy the bearer-auth JSON contract, timeout, and retry rules documented in the Audio & Media Contract.
- **FR-016**: Deleting a session MUST hard-delete session/evaluation records and cascade to delete associated LeanCloud LFiles; LObject references are removed; no soft delete.
- **FR-017**: Upon session completion, the system MUST execute the Evaluation Flow Contract (enqueue job, text-only LLM scoring per scenario-defined skills, 1–5 rubric with notes, retry/backoff, relaxed SC-003 SLO).
- **FR-018**: Evaluation APIs MUST expose status and serve cached results exactly as defined in the Evaluation Flow Contract (pending/failed/completed states, no re-evaluation on repeat views).
- **FR-019**: System MUST list historical practice sessions with filters/sorting (e.g., by date, scenario) and provide access to detail view including transcript, audio references, and evaluation; default sort newest-first, page size 20, filters by scenario and category, search by title/objective substring.
- **FR-020**: System MUST allow the trainee to start a new session using any previously saved scenario, preserving the original session data intact.
- **FR-021**: System MUST validate scenario completeness (personas, objectives, end criteria) before allowing practice to start and return actionable errors for missing fields.
- **FR-022**: System MUST retain transcripts and audio until the trainee deletes them and provide a way to delete specific sessions and associated media.

### Non-Functional Requirements

- **NFR-001**: Size infrastructure and concurrency controls for fewer than 20 simultaneous practice sessions (single-team pilot load), ensuring graceful degradation if exceeded.

### Key Entities *(include if feature involves data)*

- **Scenario**: Category, title, description, objective, participant personas/backgrounds, end
  criteria, and prompts for AI initiation.
- **PracticeSession**: Scenario reference, start/end timestamps, duration, termination reason, status.
- **Turn**: PracticeSession reference, speaker (trainee or AI), transcript text, audio LeanCloud file
  reference/URL (MP3), timestamp, and sequence order; trainee turns include context text and transcript
  derived via qwen3-omni-flash ASR; AI turns include transcript returned with audio.
- **Evaluation**: PracticeSession reference, ratings per scenario-defined communication skill (from a
  global skill library), qualitative feedback, evaluator source, created timestamp; ratings use
  numeric 1–5 scale with rubric-aligned per-skill notes and overall summary.

### Supporting Contracts

#### Session Lifecycle Contract

- A session starts when a trainee selects a validated scenario (complete personas, objectives, end criteria) and reviews it; the AI initiates the first turn using the scenario persona and context.
- Turns alternate trainee ↔ AI. After each trainee upload, the backend immediately triggers the AI reply while separately handling ASR.
- The client measures idle time (default 8s) and total session duration (default 5m, overridable per scenario), attaching session start and per-turn timestamps to every request.
- The server recalculates timers; if drift exceeds 2 seconds, server values override client reports. The server is the source of truth for session state and termination reasons.
- Sessions end when: the trainee manually stops, the client closes, idle or total duration exceeds thresholds, or the per-turn objective check decides the goal succeeded/failed. Termination reasons are stored with the session.
- After every AI reply, the server invokes a configurable text-only objective-check model; if it reports success/failure, the server ends the session immediately and records the cause.
- Termination events are pushed over WebSocket with a poll-after-turn fallback; server decisions win on disagreement.

#### Audio & Media Contract

- Each turn transports a base64 MP3 blob (mono ~32 kbps) kept under LeanCloud's 128 KB LFile limit; clients pre-validate size and surface clear errors if exceeded.
- Trainee requests include audio plus optional context text. On receipt, the backend uploads the audio to LeanCloud LFile via REST (relying on LeanCloud encryption) and stores only the resulting reference/metadata in LObject records.
- Immediately after receiving a trainee turn, the backend (1) calls qwen3-omni-flash generation with persona/system text, context, conversation history, and the base64 MP3; it expects JSON with AI transcript + base64 MP3 audio, enforces a 10s timeout, and retries up to two times on 5xx/timeout responses; (2) asynchronously calls qwen3-omni-flash ASR with the trainee audio to obtain the trainee transcript without delaying the AI reply; retries preserve turn order.
- Qwen generation uses the OpenAI-compatible SDK (Python ≥1.52.0) against `https://dashscope.aliyuncs.com/compatible-mode/v1` with bearer auth (`DASHSCOPE_API_KEY`, mirrored in `QWEN_BEARER`). Requests MUST set `stream=True`, specify `modalities=["text","audio"]`, and pass `audio={"voice": "<voiceId>", "format": "wav"}`; responses stream chunks containing incremental text plus base64 WAV audio that the backend decodes.
- AI turns persist both the returned transcript and uploaded audio reference. Trainee turns persist the ASR transcript once available plus the audio reference; missing/corrupted audio triggers a retry prompt without corrupting the session record.
- The backend converts the returned WAV/PCM to mono ~32 kbps MP3 (e.g., via ffmpeg/pydub) before storing in LeanCloud, ensuring transport compatibility while the model contract remains satisfied.
- Raw base64 audio is never stored outside LeanCloud LFiles; session/turn records keep speaker role, timestamps, transcripts, and LFile identifiers only. Audio and transcripts remain until the trainee deletes the session, which must cascade to delete associated files.

#### Evaluation Flow Contract

- Each scenario lists communication skills chosen from a shared skill library; only those skills are scored for that session.
- When a session ends, the system triggers an asynchronous evaluation task that compiles transcripts/audio metadata and calls a configurable text-only LLM to score each skill on a 1–5 rubric (1=poor, 3=adequate, 5=excellent), attach per-skill notes, and generate an overall summary of strengths/gaps.
- Evaluations run via FastAPI in-process background tasks with status fields `pending`, `running`, `failed`, and `completed`; the task engine retries with backoff while the API instance remains healthy, and trainees can requeue jobs via API if additional attempts are needed.
- The default evaluator is the GPT-5 mini endpoint hosted at `https://api.chataiapi.com/v1/chat/completions`. Requests use bearer `secretKey`, include `{"model":"gpt-5-mini","messages":[...]}` payloads, and responses return OpenAI-style `choices` plus moderation metadata; the backend extracts ratings/feedback from the assistant message and records token usage for observability.
- Trainees poll/fetch evaluation status; once completed, stored ratings/feedback are re-used for subsequent views without re-triggering the evaluator.

#### Observability & Metrics Contract

- Emit structured logs for every session and turn capturing session ID, turn ID, latency, and termination reasons; logs feed troubleshooting and auditing.
- Publish metrics that align with success criteria SC-001 to SC-004: session completion rate, termination latency, evaluation turnaround, and ability to open history items within two steps.
- Instrument OpenTelemetry-style traces covering request → AI call → storage so that latency hotspots are visible end-to-end.

## Assumptions & Dependencies

- Scenario library is curated and validated for completeness (personas, objectives, end criteria)
  before being published for practice, enabling the Session Lifecycle Contract to enforce prerequisites.
- The Audio & Media Contract assumes qwen3-omni-flash (or a stub) can generate speech plus text each
  turn; testing environments provide safe fallbacks when the service is unavailable.
- The Evaluation Flow Contract assumes a text-only evaluator that consumes transcripts/audio metadata
  and produces structured rubric scores with notes.
- Default timer values (8-second idle, 5-minute total unless a scenario overrides) come from the
  Session Lifecycle Contract; clients measure locally while servers validate.
- Audio & Media Contract governs data retention (indefinite until deletion), codec/size rules, LeanCloud
  storage via REST, retries, and the split between speech generation and text-only models.
- Asynchronous ASR + evaluation tasks ride on FastAPI background tasks (in-process asyncio); MVP
  scope accepts best-effort durability with manual requeue mechanisms if the API restarts mid-task.
- No authentication in this release; identity remains a single-tenant stub, and admin scenario seeding
  is handled out-of-band (no admin UI).
- Observability tooling follows the Observability & Metrics Contract (structured logs, metrics, traces).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of initiated sessions complete with a recorded termination reason and saved
  transcript/audio without system errors.
- **SC-002**: 95% of sessions meeting end criteria or timeout stop within 2 seconds of detection and
  persist the final state.
- **SC-003**: 90% of evaluations deliver ratings and feedback to the trainee within 60 seconds of
  session completion (reflects async FastAPI background tasks + retries).
- **SC-004**: 95% of trainees can locate and open a past session with transcript and feedback in under
  two steps from the history list.

## Clarifications

### Session 2025-12-06
- Q: How long should transcripts and audio be retained? → A: Audio & Media Contract: retain until the trainee deletes the session.
- Q: How is user speech turned into text for turns? → A: Audio & Media Contract: trainee sends audio + optional context, backend triggers immediate AI reply and asynchronous qwen ASR transcription.
- Q: What audio format/flow and fallback should be used? → A: Audio & Media Contract: base64 MP3 per turn (<128 KB, ~32 kbps mono) with retries that preserve prior turns.
- Q: How should evaluations score communication skills? → A: Evaluation Flow Contract: numeric 1–5 rubric with per-skill notes plus overall summary.
- Q: How are skills selected for scoring? → A: Evaluation Flow Contract: each scenario references a skill subset from the global library.
- Q: Where are idle/timeout timers measured? → A: Session Lifecycle Contract: client measures and reports, server recalculates and is authoritative.
- Q: How is audio stored and where? → A: Audio & Media Contract: LeanCloud LFiles via REST with only references stored in turn/session records.
- Q: How should history listing paginate/sort/filter/search? → A: Page size 20, newest-first; filter by scenario and category; search title/objective substring.
- Q: What is the auth scope/roles for this release? → A: No auth (public); identity stubbed; scenario seeding out-of-band; admin UI deferred.
- Q: What observability signals are required? → A: Observability & Metrics Contract: structured logs, metrics mapped to SC-001–SC-004, and traces across request → AI call → storage.
- Q: What rate limiting applies? → A: None for this release.
- Q: Any accessibility/localization requirements? → A: None specified for this release.
- Q: What per-turn audio size cap/encryption applies? → A: Audio & Media Contract: single-turn MP3 must stay under the 128 KB LeanCloud limit; LeanCloud encryption + HTTPS cover storage/transit.
- Q: What is the qwen3-omni-flash API contract? → A: Audio & Media Contract: bearer auth JSON calls that include persona/system text + MP3 input and return MP3 + transcript with 10s timeout and two retries on 5xx/timeouts.
- Q: How are client timers validated? → A: Session Lifecycle Contract: client sends start/per-turn timestamps; server recalculates, tolerates ≤2s drift, otherwise overrides.
- Q: Do we store raw base64 in session records in addition to LeanCloud files? → A: Audio & Media Contract: only LeanCloud references/metadata live in turn/session records.
- Q: Is evaluation synchronous or async? → A: Evaluation Flow Contract: async FastAPI background tasks with status + retry (best effort), results polled until ready.
- Q: How do deletes work? → A: Audio & Media Contract + FR-016: hard delete session/evaluation records and cascade to LeanCloud files; no soft delete.
- Q: What are the session end conditions? → A: Session Lifecycle Contract: manual stop, client close, timer breach, or text-only objective check deciding success/failure.
- Q: Are during-session and post-session models tied to qwen3-omni-flash? → A: Session Lifecycle + Evaluation Flow Contracts: both objective checks and post-session evaluations use configurable text-only models (not the speech model).
- Q: How are qwen generation calls authenticated and formatted? → A: Use the DashScope OpenAI-compatible SDK (Python ≥1.52.0) with `stream=True`, `modalities=["text","audio"]`, and `audio={"voice": "...", "format": "wav"}`; decode streamed WAV chunks locally, convert to mono MP3, and store LeanCloud references only.
- Q: Which text-only evaluator backs post-session scoring? → A: GPT-5 mini served at `https://api.chataiapi.com/v1/chat/completions`, authenticated via bearer `secretKey` using OpenAI-style chat payloads; the assistant response provides rubric scores/notes that we persist.
- Q: How do ASR and generation calls differ? → A: Audio & Media Contract: generation returns audio+transcript synchronously; ASR is an async audio-only call that feeds trainee transcripts without blocking the AI reply.
- Q: How are termination signals transported? → A: Session Lifecycle Contract: server pushes WebSocket termination events with poll fallback and authoritative decision.
- Q: How is async evaluation executed? → A: Evaluation Flow Contract: FastAPI background tasks mark LeanCloud records and retry with backoff while the API remains available; manual requeue is exposed for additional attempts.
- Q: How do we fit 128 KB audio? → A: Audio & Media Contract: enforce mono ~32 kbps MP3 (<3s) and fail fast on oversized uploads.
- Q: How is identity handled in single-tenant mode? → A: Use a fixed stub user ID to scope sessions/history/deletes and avoid cross-user leakage.
- Q: Where to emit observability data? → A: Observability & Metrics Contract: OpenTelemetry-style spans + LeanCloud logging with session/turn IDs, latencies, termination reasons, and metrics tied to SC-001–SC-004.
- Q: Do we ever store raw base64 outside LeanCloud files? → A: Audio & Media Contract: raw audio stays in-memory for upload/ASR; only references + transcripts reach persistent storage.
- Q: Who is the termination authority? → A: Session Lifecycle Contract: server decides and pushes termination events; client reports telemetry only.

### Session 2025-12-07
- Q: What concurrent session load should the system target? → A: Size for fewer than 20 simultaneous sessions (single-team pilot scale).
