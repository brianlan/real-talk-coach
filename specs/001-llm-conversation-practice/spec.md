# Feature Specification: LLM Conversation Practice Coach

**Feature Branch**: `001-llm-conversation-practice`  
**Created**: 2025-12-06  
**Status**: Draft  
**Input**: User description: "- This is an app that contains both backend API and frontend UI that leverages the power of LLM (both text and speech) to help people to practice communication skills in everyday scenarios. For example, we may encounter a situation that I have to end a relationship with my lover, or express opposite opinions of my boss, or let my room mate to move away, etc. We define a scenario as a structure that contains the following properties: - Scenario category - Scenario title - Detailed description of the conversation including background and context. - Objective of the conversation - Two parties in the conversation (personal backgrounds and AIs persona).
  - Conversation End Criteria (e.g. objective achieved, or any party got pissed off) . A typical practice would look as follows:
  - The trainee selects a scenario from the scenario pool.
  - The trainee reads all the needed information of the scenario.
  - AI initiates the discussion, and the trainee and the AI will talk round by round. The AI will play the role that has predefined background and persona in the scenario settings.
  - Each round, AI evaluates whether the end criteria of the conversion has met. If not, continue playing the role and talk, otherwise, end the conversation.   - The conversation can also be ended by other logic other than the evaluation by AI. For example, if the trainee hasnt provide a response for more than 8 seconds or the total time elapsed exceeds a predefined threshold, say 5 minutes. - After the practice/converstion ends, all the information will be provided to another pure-text-based LLM to evaluate this practice and provide the user with: - Ratings on each communication skills that relates to the scenario in the practice, including skills that performed by the user, or the user lacks. - Provide general feedbacks on what has been done well and where can be improved. During the practice, well use/call qwen3-omni-flash (https://bailian.console.aliyun.com/?tab=doc#/doc/?type=model&url=2867839) as the AI assistant, where after the role settings are provided, the AI uses this model to generate audio directly (output both audio and text).  Likewise, the users audio is also directly passed to this model together with statement text like reply according to the audio content and the conversation history. All the related information of each practice will be saved into a database including the raw audio base64 that the user and AI outputs. The user can view all the historical practices in a list. The user can click to view the details of any of them or start practicing the same scenario again from an existing practice. Create a python tech stack based api server using FastAPI, httpx, uvicorn and pydantic, etc. and follow best practices of building such an API server. Use"

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

- **FR-001**: System MUST provide a catalog of practice scenarios capturing category, title,
  description, objective, participant backgrounds/personas, and explicit end criteria.
- **FR-002**: Trainee MUST be able to start a practice session by selecting a scenario and reviewing
  its details before the AI initiates the first turn in the specified persona.
- **FR-003**: System MUST run turn-based conversations where the AI and trainee alternate, checking
  end criteria after each round and allowing termination due to idle time or maximum duration.
- **FR-004**: System MUST capture and persist each turn's transcript and associated audio (base64) for
  both AI and trainee, with timestamps and speaker roles.
- **FR-005**: Trainee MUST be able to manually end a session at any time, with termination reason
  recorded.
- **FR-006**: Upon session completion, system MUST compile conversation data and request evaluation
  from a text-only model to produce ratings per relevant communication skills and narrative feedback.
- **FR-007**: System MUST present stored ratings and feedback to the trainee for each session without
  requiring re-evaluation on repeat views.
- **FR-008**: System MUST list historical practice sessions with filters/sorting (e.g., by date,
  scenario) and provide access to detail view including transcript, audio references, and evaluation.
- **FR-009**: System MUST allow the trainee to start a new session using any previously saved
  scenario, preserving the original session data intact.
- **FR-010**: System MUST validate scenario completeness (personas, objectives, end criteria) before
  allowing practice to start and return actionable errors for missing fields.

### Key Entities *(include if feature involves data)*

- **Scenario**: Category, title, description, objective, participant personas/backgrounds, end
  criteria, and prompts for AI initiation.
- **PracticeSession**: Scenario reference, start/end timestamps, duration, termination reason, status.
- **Turn**: PracticeSession reference, speaker (trainee or AI), transcript text, audio base64,
  timestamp, and sequence order.
- **Evaluation**: PracticeSession reference, ratings per communication skill, qualitative feedback,
  evaluator source, created timestamp.

## Assumptions & Dependencies

- Trainees are authenticated/identified so session history can be tied to individuals.
- Scenario library is curated and validated for completeness (personas, objectives, end criteria)
  before being published for practice.
- AI voice/text service returns both text and audio per turn; a safe fallback or stub is available for
  testing when the service is unavailable.
- Text-only evaluator can consume transcripts (and optional audio metadata) to return structured
  ratings and feedback.
- Default timeouts: idle threshold of 8 seconds and maximum session duration of 5 minutes unless a
  scenario defines stricter limits.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of initiated sessions complete with a recorded termination reason and saved
  transcript/audio without system errors.
- **SC-002**: 95% of sessions meeting end criteria or timeout stop within 2 seconds of detection and
  persist the final state.
- **SC-003**: 90% of evaluations deliver ratings and feedback to the trainee within 10 seconds of
  session completion.
- **SC-004**: 95% of trainees can locate and open a past session with transcript and feedback in under
  two steps from the history list.
