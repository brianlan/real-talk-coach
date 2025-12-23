# Practice Coach Architecture

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
