# Quickstart

## Prerequisites
- Python 3.11 + pipx or uv
- Node.js 20 LTS + pnpm 9
- Redis 7 (for Celery broker/backing store)
- LeanCloud single-tenant credentials (appId, appKey, masterKey)
- qwen3-omni-flash + evaluator model API keys

## Environment Variables
Create `.env` files in both apps (never commit secrets):

`backend/.env`
```
LEAN_APP_ID=xxx
LEAN_APP_KEY=xxx
LEAN_MASTER_KEY=xxx
LEAN_SERVER_URL=https://api.leancloud.cn
QWEN_BASE_URL=https://api.qwen.com
QWEN_BEARER=...
EVALUATOR_MODEL=qwen-text-eval
STUB_USER_ID=pilot-user
REDIS_URL=redis://localhost:6379/0
```

`frontend/.env.local`
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_WS_BASE=ws://localhost:8000/ws
```

## Install
```bash
cd backend
uv sync  # or pip install -r requirements.txt
cd ../frontend
pnpm install
```

## Run (dev)
Terminal 1 – backend API + worker:
```bash
cd backend
uvicorn app.main:app --reload
```

Terminal 2 – Celery evaluation worker:
```bash
cd backend
celery -A app.workers.evaluations worker -l info
```

Terminal 3 – frontend:
```bash
cd frontend
pnpm dev --port 3000
```

## Testing & Linting
```bash
cd backend
ruff check .
pytest

cd ../frontend
pnpm lint
pnpm test
pnpm playwright test   # e2e, uses stubbed qwen/LeanCloud MSW handlers
```

## Mocking External Services
- Backend tests use httpx MockTransport for qwen and LeanCloud.
- Frontend tests rely on MSW handlers seeded with canned scenarios.
- Audio uploads in dev mode save to temp files + fake LeanCloud IDs.

## Smoke Flow
1. Seed scenarios via `/scripts/seed_scenarios.py`.
2. Visit `http://localhost:3000`, pick a scenario, start practice.
3. Exchange a few turns (browser mic permission required).
4. Wait for evaluation ready toast, then open history and replay.

## Deployment Notes
- Package backend as container image with uvicorn + gunicorn workers, horizontal pod autoscale
  capped for <20 concurrent sessions.
- Deploy frontend via static hosting (Vercel/S3) pointing to API base.
- Redis + Celery worker share the same VPC; LeanCloud + qwen secrets stored via runtime secret
  manager.
