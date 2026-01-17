#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Running backend checks..."
cd "${root_dir}/backend"
ruff check .
pytest

echo "Running frontend checks..."
cd "${root_dir}/frontend"
pnpm lint
pnpm test
pnpm playwright test
