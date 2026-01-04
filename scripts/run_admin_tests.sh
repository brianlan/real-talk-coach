#!/usr/bin/env bash
set -euo pipefail

# Runs admin-focused suites for both backend and frontend.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend contract tests (admin)"
(
  cd "$PROJECT_ROOT/backend"
  pytest tests/contract/test_admin_skills.py \
         tests/contract/test_admin_scenarios.py \
         tests/contract/test_admin_sessions.py \
         tests/contract/test_admin_audit_log.py
)

echo "==> Backend integration tests (admin)"
(
  cd "$PROJECT_ROOT/backend"
  pytest tests/integration/test_admin_skills_flow.py \
         tests/integration/test_admin_scenarios_flow.py \
         tests/integration/test_admin_sessions_flow.py
)

echo "==> Frontend unit/e2e tests (admin)"
(
  cd "$PROJECT_ROOT/frontend"
  pnpm test
)
(
  cd "$PROJECT_ROOT/frontend"
  pnpm run playwright -- tests/e2e/admin-skills.spec.ts \
                        tests/e2e/admin-scenarios.spec.ts \
                        tests/e2e/admin-sessions.spec.ts
)

echo "All admin suites completed."
