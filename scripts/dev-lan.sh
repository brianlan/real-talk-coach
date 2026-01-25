#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"
CERT_DIR="$FRONTEND_DIR/.certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

PID_BACKEND="$LOG_DIR/dev-lan-backend.pid"
PID_FRONTEND="$LOG_DIR/dev-lan-frontend.pid"
PID_PROXY="$LOG_DIR/dev-lan-proxy.pid"

LOG_BACKEND="$LOG_DIR/backend-dev.log"
LOG_FRONTEND="$LOG_DIR/frontend-dev.log"
LOG_PROXY="$LOG_DIR/frontend-https-proxy.log"

LAN_IP=""
DO_STOP=0
DO_MKCERT=0

usage() {
  cat <<'USAGE'
Usage: scripts/dev-lan.sh [--lan-ip <ip>] [--mkcert] [--stop]

Options:
  --lan-ip <ip>  LAN IP to use in printed URLs and env (default: auto-detect)
  --mkcert       Generate/refresh certs using mkcert
  --stop         Stop LAN dev processes started by this script
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lan-ip)
      LAN_IP="${2:-}"
      shift 2
      ;;
    --mkcert)
      DO_MKCERT=1
      shift
      ;;
    --stop)
      DO_STOP=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$LAN_IP" ]]; then
  if command -v ip >/dev/null 2>&1; then
    LAN_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')"
  fi
fi
if [[ -z "$LAN_IP" ]]; then
  LAN_IP="192.168.71.57"
fi

stop_pid() {
  local label="$1"
  local pid_file="$2"
  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Stopping $label (pid $pid)"
    kill "$pid" || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      echo "Warning: $label still running (pid $pid)"
    fi
  fi
  rm -f "$pid_file"
}

if [[ "$DO_STOP" -eq 1 ]]; then
  stop_pid "frontend https proxy" "$PID_PROXY"
  stop_pid "frontend dev" "$PID_FRONTEND"
  stop_pid "backend" "$PID_BACKEND"
  exit 0
fi

mkdir -p "$LOG_DIR"

if [[ "$DO_MKCERT" -eq 1 ]]; then
  if ! command -v mkcert >/dev/null 2>&1; then
    echo "mkcert is not installed. Install mkcert and try again." >&2
    exit 1
  fi
  mkdir -p "$CERT_DIR"
  mkcert -install
  mkcert -cert-file "$CERT_FILE" -key-file "$KEY_FILE" \
    "$LAN_IP" localhost 127.0.0.1 ::1
fi

if [[ ! -f "$CERT_FILE" || ! -f "$KEY_FILE" ]]; then
  echo "Missing certs in $CERT_DIR. Run with --mkcert to generate." >&2
  exit 1
fi

export NEXT_PUBLIC_API_BASE="https://$LAN_IP:8443"
export NEXT_PUBLIC_WS_BASE="wss://$LAN_IP:8443/ws"
export NODE_TLS_REJECT_UNAUTHORIZED=0
export LAN_IP

(
  cd "$BACKEND_DIR"
  nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8443 \
    --ssl-keyfile "../frontend/.certs/key.pem" \
    --ssl-certfile "../frontend/.certs/cert.pem" \
    --env-file .env > "$LOG_BACKEND" 2>&1 &
  echo $! > "$PID_BACKEND"
)

(
  cd "$FRONTEND_DIR"
  nohup pnpm dev --hostname 0.0.0.0 --port 3000 > "$LOG_FRONTEND" 2>&1 &
  echo $! > "$PID_FRONTEND"
)

(
  cd "$FRONTEND_DIR"
  nohup node https-dev-server.cjs > "$LOG_PROXY" 2>&1 &
  echo $! > "$PID_PROXY"
)

cat <<EOF
LAN dev started.
- Frontend (HTTPS): https://$LAN_IP:3443
- Backend (HTTPS API): https://$LAN_IP:8443
Logs: $LOG_DIR
Stop: scripts/dev-lan.sh --stop
EOF
