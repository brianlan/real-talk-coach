# Admin Measurement Checks (SC-001..SC-004)

## SC-001 – Scenario publish time
- **Goal**: Admins publish a new scenario with assigned skills in < 5 minutes.
- **How to measure**:
  1. Start timer when admin opens `/admin/scenarios/new` with at least one skill available.
  2. Record timestamps for each major step (fill personas, assign skills, publish).
  3. Stop timer when publish confirmation returns from API.
- **Instrumentation**: Capture client-side performance entries tagged `admin-scenario-publish`. Log to console/network for manual runs. Future enhancement: send to telemetry endpoint.

## SC-002 – Publish success rate
- **Goal**: ≥95% of publish attempts succeed without support.
- **How to measure**:
  1. Count total publish requests vs. those returning HTTP 200/201.
  2. Track error categories (validation, conflict, server) via toast surface instrumentation.
- **Instrumentation**: Wrap `publishScenario` client call to emit analytics event with status. Export weekly metrics via ops dashboard.

## SC-003 – Search speed
- **Goal**: Admins locate a specific scenario/skill via search/filter in ≤30 seconds.
- **How to measure**:
  1. When filters/search applied in `/admin/skills` or `/admin/scenarios`, record timestamp.
  2. When list updates, capture elapsed time and show in devtools logs.
  3. Manual QA: note actual seconds from action to entry view.
- **Instrumentation**: Frontend already loads lists client-side; add optional `console.info` hooks (behind `NEXT_PUBLIC_ENABLE_ADMIN_METRICS`).

## SC-004 – Data quality (published scenarios complete)
- **Goal**: 0 published scenarios missing required fields or skills.
- **How to measure**:
  1. Nightly job or manual script hitting `/api/admin/scenarios?status=published`.
  2. Validate each record has required fields and skills length > 0.
  3. Report violations count; should be 0.
- **Instrumentation**: Provide script snippet in `scripts/check_scenarios.py` (future) or manual query via LeanCloud console.

## Running the checks
1. Enable `NEXT_PUBLIC_ENABLE_ADMIN_METRICS=1` for client instrumentation logs.
2. Run through scenario/skill flows and record durations/errors.
3. For SC-004, execute the validation script (to be added) or manually audit LeanCloud data before release.
4. Document findings in release notes.
