# Real Talk Coach

## Prerequisites
- Python 3.11 + pipx or uv
- Node.js 20 LTS + pnpm 9
- LeanCloud single-tenant credentials (appId, appKey, masterKey)
- qwen3-omni-flash + evaluator model API keys (DashScope OpenAI-compatible SDK >=1.52.0)
- GPT-5 mini secretKey (https://api.chataiapi.com)

## Environment
Create `.env` files in both apps (never commit secrets). Use the examples below as a starting point:

- `backend/.env.example`
- `frontend/.env.local.example`

## Install
```bash
cd backend
uv sync  # or pip install -r requirements.txt
# ensure qwen helpers are installed (inside uv/virtualenv):
# uv pip install "openai>=1.52.0" numpy soundfile pydub ffmpeg-python

cd ../frontend
corepack enable  # ensures pnpm is available
pnpm install
```

## Run (dev)
Terminal 1 – backend API (serves REST/WebSockets and launches background tasks for ASR/evaluations):
```bash
cd backend
uvicorn app.main:app --reload --env-file .env
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
pnpm playwright test
```

## Seed sample data
```bash
python scripts/seed_scenarios.py \
  --skills specs/001-llm-conversation-practice/seed-data/sample-skills.json \
  --scenarios specs/001-llm-conversation-practice/seed-data/sample-scenarios.json
```
