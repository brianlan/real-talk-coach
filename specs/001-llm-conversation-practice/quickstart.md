# Quickstart

## Prerequisites
- Python 3.11 + pipx or uv
- Node.js 20 LTS + pnpm 9
- LeanCloud single-tenant credentials (appId, appKey, masterKey)
- qwen3-omni-flash + evaluator model API keys (DashScope OpenAI-compatible SDK ≥1.52.0; install `openai`,
  plus `numpy`, `soundfile`, and an MP3 encoder helper such as `pydub` + `ffmpeg` for WAV→MP3 conversion)
- GPT-5 mini `secretKey` for evaluations (https://api.chataiapi.com)

## Environment Variables
Create `.env` files in both apps (never commit secrets):

`backend/.env`
```
LEAN_APP_ID=xxx
LEAN_APP_KEY=xxx
LEAN_MASTER_KEY=xxx
LEAN_SERVER_URL=https://api.leancloud.cn
DASHSCOPE_API_KEY=...  # DashScope/OpenAI SDK key used for qwen3-omni-flash calls
QWEN_BEARER=...        # optional alias if other components expect this name
CHATAI_API_BASE=https://api.chataiapi.com/v1
CHATAI_API_KEY=...
CHATAI_API_MODEL=gpt-5-mini
EVALUATOR_MODEL=gpt-5-mini  # kept for backwards compatibility in configs/tests
OBJECTIVE_CHECK_API_BASE=${CHATAI_API_BASE}  # defaults to evaluator endpoint unless overridden
OBJECTIVE_CHECK_API_KEY=${CHATAI_API_KEY}
OBJECTIVE_CHECK_MODEL=gpt-5-mini
STUB_USER_ID=pilot-user
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
# ensure qwen helpers are installed (inside uv/virtualenv):
# uv pip install "openai>=1.52.0" numpy soundfile pydub ffmpeg-python
cd ../frontend
pnpm install
```

## Run (dev)
Terminal 1 – backend API (serves REST/WebSockets and launches background tasks for ASR/evaluations):
```bash
cd backend
uvicorn app.main:app --reload
```

Terminal 2 – frontend:
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
1. Seed scenarios via `/scripts/seed_scenarios.py` (see Scenario Seeding Notes below for current status).
2. Visit `http://localhost:3000`, pick a scenario, start practice.
3. Exchange a few turns (browser mic permission required).
4. Wait for evaluation ready toast, then open history and replay.

### Scenario & Skill Seeding Notes
- **Script contract**: `python scripts/seed_scenarios.py --skills specs/001-llm-conversation-practice/seed-data/sample-skills.json --scenarios specs/001-llm-conversation-practice/seed-data/sample-scenarios.json`. The script (TBD) will upsert Skill records first (using the `externalId` field for deterministic lookups), then create Scenario LObjects that reference the corresponding LeanCloud `objectId`s. It requires the LeanCloud env vars listed above plus `STUB_USER_ID`.
- **Status**: Script implementation is TBD; until it lands, import `seed-data/sample-skills.json` into the `Skill` class and `seed-data/sample-scenarios.json` into the `Scenario` class via the LeanCloud dashboard (`Data > <Class> > Import > JSON`) so smoke tests have seed data.
- **Format**: Sample files in `specs/001-llm-conversation-practice/seed-data/` illustrate the schema for both skills (including `externalId`) and scenarios; update them (or provide your own) before running the script once it exists.
- **Skill mapping**: Scenario `skills` entries contain skill `externalId`s; the script matches them to the Skill objects it just upserted and stores the resulting LeanCloud `objectId` array on each Scenario.

## Deployment Notes
- Package backend as container image with uvicorn + gunicorn workers, horizontal pod autoscale
  capped for <20 concurrent sessions; background tasks share the same process pool so size pods to
  leave a little headroom for ASR/evaluation coroutines.
- Deploy frontend via static hosting (Vercel/S3) pointing to API base.
- LeanCloud + qwen secrets stored via runtime secret manager.
- Ensure the backend container includes `ffmpeg` (or another encoder) so streamed WAV audio from Qwen
  can be transcoded to mono ≤24 kbps MP3 before uploading to LeanCloud.
