# Practice Coach Architecture

## Architecture Summary
- **Backend**: FastAPI + Uvicorn with async HTTP/WebSocket handlers and in-process background tasks.
- **Frontend**: Next.js 15 App Router; practice room uses Web Audio + WebSocket streams.
- **Storage**: LeanCloud LObject/LFile via REST; no additional DB.
- **LLMs**: qwen3-omni-flash for audio generation/ASR; GPT-5 mini for objective checks + evaluations.

## API Surface (Primary)
- `GET /api/scenarios` / `GET /api/skills` for catalog metadata.
- `POST /api/sessions` to start sessions; `POST /api/sessions/{id}/turns` for audio turns.
- `GET /api/sessions` / `GET /api/sessions/{id}` for history list/detail (requires `historyStepCount`).
- `POST /api/sessions/{id}/manual-stop` and `DELETE /api/sessions/{id}` for lifecycle control.
- `GET/POST /api/sessions/{id}/evaluation` for evaluation status + requeue.
- `POST /api/sessions/{id}/practice-again` to restart from prior scenario.
- `WS /ws/sessions/{id}` for `ai_turn`, `termination`, and `evaluation_ready` events.

## Core Flows
### Session Lifecycle
1. Client starts session (`POST /api/sessions`) with `clientSessionStartedAt`.
2. Server enforces drift and capacity caps; persists `PracticeSession`.
3. Session initializes AI turn 0 via `turn_pipeline`, emits WebSocket `ai_turn`.
4. Trainee turns are uploaded; server stores audio in LeanCloud, triggers qwen generation + ASR.
5. Objective checks run after AI replies; terminal status sets `terminationReason`.
6. Terminal state enqueues evaluation runner; WebSocket emits `evaluation_ready` when complete.

### Evaluation Flow
1. `evaluation_runner.enqueue()` creates/updates Evaluation record with `pending` status.
2. Background task calls GPT-5 mini with a tool-call schema for rubric scores.
3. Retries use backoff within the API process; status transitions to `completed` or `failed`.
4. Completed evaluations emit queue-latency metrics and WebSocket `evaluation_ready`.
5. Requeue allowed only from `failed` state via `POST /api/sessions/{id}/evaluation`.

### History + Replay
1. `GET /api/sessions` returns paginated history sorted by `startedAt`.
2. `GET /api/sessions/{id}` returns turns + evaluation; signed audio URLs (TTL 15m).
3. UI refreshes signed URLs on demand if playback fails.
4. `POST /api/sessions/{id}/practice-again` spawns a new session with the same scenario.

## Saturation Runbook (Pilot Capacity)

### Trigger
- Metric: `pilot.capacity_exceeded` emitted when the concurrent session cap is hit.
- Symptoms: `POST /api/sessions` responds with HTTP 429 and message "pilot capacity exceeded".

### Expected Behavior
- The API refuses new sessions once:
  - `active` (non-ended) sessions >= 20, or
  - `pending` sessions >= 5.
- Existing sessions continue to function normally.

### Immediate Actions
1. Verify current counts in LeanCloud (PracticeSession records) to confirm active/pending totals.
2. Ask trainees to retry after idle sessions end or are manually stopped.
3. Monitor the rate of new session creation attempts and 429 responses.

### Mitigation Options
- **Short-term**: Manually end stale sessions that are stuck in `pending` or `active`.
- **Operational**: Increase session cap only if CPU/memory headroom and qwen rate limits allow.
- **Product**: Queue users in the UI and retry automatically with exponential backoff.

### Follow-up
- Review logs for `pilot.capacity_exceeded` events and identify spikes.
- If frequent, consider scaling the FastAPI deployment or reducing per-session resource usage.
