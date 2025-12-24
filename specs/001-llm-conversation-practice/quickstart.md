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
- Browser recordings are captured as low-bitrate WebM/Opus; the backend transcodes to MP3 before LeanCloud upload to meet the 128 KB constraint.

## Smoke Flow
1. Seed scenarios via `python scripts/seed_scenarios.py --skills specs/001-llm-conversation-practice/seed-data/sample-skills.json --scenarios specs/001-llm-conversation-practice/seed-data/sample-scenarios.json` (see Scenario & Skill Seeding Notes for CLI guidance).
2. Visit `http://localhost:3000`, pick a scenario, start practice.
3. Observe the AI initiation turn streaming automatically, then exchange a few turns (browser mic permission required).
4. Wait for evaluation ready toast, then open history and replay (history requests include the required `historyStepCount` query parameter so telemetry works).

### Scenario & Skill Seeding Notes
- **Script contract**: Run `python scripts/seed_scenarios.py --skills specs/001-llm-conversation-practice/seed-data/sample-skills.json --scenarios specs/001-llm-conversation-practice/seed-data/sample-scenarios.json`. The helper upserts all Skill records via `externalId`, then creates Scenario LObjects referencing the resulting LeanCloud IDs, logging per-record success/failure and exiting non-zero on validation errors.
- **Fallback**: If the script fails, temporarily import `seed-data/*.json` through the LeanCloud dashboard and capture the manual steps in your runbook; treat this as an exception rather than the default workflow.
- **Format**: Sample files in `specs/001-llm-conversation-practice/seed-data/` illustrate the schema for both skills (including `externalId`) and scenarios; copy or edit them before rerunning the script.
- **Skill mapping**: Scenario `skills` entries contain skill `externalId`s; the script matches them to the Skill objects it just upserted and stores the resulting LeanCloud `objectId` array on each Scenario.
- **Verification**: Successful runs print a summary such as `Seed complete: 4 skills, 6 scenarios`; investigate any non-zero exit status or missing counts before proceeding.

## Deployment Notes
- Package backend as container image with uvicorn + gunicorn workers, horizontal pod autoscale
  capped for <20 concurrent sessions; background tasks share the same process pool so size pods to
  leave a little headroom for ASR/evaluation coroutines.
- Deploy frontend via static hosting (Vercel/S3) pointing to API base.
- LeanCloud + qwen secrets stored via runtime secret manager.
- Ensure the backend container includes `ffmpeg` (or another encoder) so streamed WAV audio from Qwen
  can be transcoded to mono ≤24 kbps MP3 before uploading to LeanCloud.
