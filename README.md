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

## Remote/LAN dev (access from another machine)
Recording audio requires a secure context (HTTPS). For LAN access, use the HTTPS proxy
and run backend with TLS.

Quick start:
```bash
scripts/dev-lan.sh --mkcert
```

1) Backend HTTPS (bind to all interfaces):
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8443 \
  --ssl-keyfile ../frontend/.certs/key.pem \
  --ssl-certfile ../frontend/.certs/cert.pem \
  --env-file .env
```

2) Frontend HTTP (bind to all interfaces):
```bash
cd frontend
pnpm dev --hostname 0.0.0.0 --port 3000
```

3) HTTPS proxy for the browser:
```bash
cd frontend
node https-dev-server.cjs
```

4) Frontend env for LAN:
```
NEXT_PUBLIC_API_BASE=https://<LAN_IP>:8443
NEXT_PUBLIC_WS_BASE=wss://<LAN_IP>:8443/ws
NODE_TLS_REJECT_UNAUTHORIZED=0
```
Then open `https://<LAN_IP>:3443` in the remote browser and accept the self-signed
certificate warning.

Notes:
- `NODE_TLS_REJECT_UNAUTHORIZED=0` is **dev-only** to allow Next.js server-side fetches
  against the self-signed backend cert.
- If you don’t want to disable TLS verification, use a trusted certificate instead (see below).

## Certificates (dev)
The HTTPS proxy and backend TLS use `frontend/.certs/cert.pem` and `frontend/.certs/key.pem`.
Do **not** commit private keys. Keep certs local and regenerate on each machine.

Recommended options:
1) **Local CA (mkcert)**: create a trusted dev cert on each machine, install the CA,
   and place the generated `cert.pem`/`key.pem` in `frontend/.certs/`.
2) **Self-signed** (current): works for LAN dev but requires manual browser trust and
   `NODE_TLS_REJECT_UNAUTHORIZED=0` for server-side fetches.

### Admin usage

- Set `ADMIN_ACCESS_TOKEN` (backend) and `NEXT_PUBLIC_ADMIN_TOKEN` (frontend) with the same value.
- Access `http://localhost:3000/admin` with the token header via browser extension or reverse proxy.
- Use the navigation shell to reach Skills, Scenarios, Sessions, and the new Audit Log view.
- Measurements for SC-001..SC-004 live in `docs/admin-metrics.md`.

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
