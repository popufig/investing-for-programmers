#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

MODE="${1:-dev}"   # dev | prod

# ── Load config from .env ───────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/../.env"
APP_HOST="0.0.0.0"
APP_PORT="18600"
if [ -f "$ENV_FILE" ]; then
  _host=$(grep -E '^APP_HOST=' "$ENV_FILE" | cut -d= -f2)
  _port=$(grep -E '^APP_PORT=' "$ENV_FILE" | cut -d= -f2)
  [ -n "$_host" ] && APP_HOST="$_host"
  [ -n "$_port" ] && APP_PORT="$_port"
fi

# ── Python venv & deps ───────────────────────────────────────────
cd "$SCRIPT_DIR/backend"
if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
cd "$SCRIPT_DIR"

if [ "$MODE" = "prod" ]; then
  # ── Production: build frontend, serve everything from FastAPI ────
  echo "Building frontend..."
  cd "$SCRIPT_DIR/frontend"
  if [ ! -d "node_modules" ]; then npm install; fi
  npm run build
  cd "$SCRIPT_DIR"

  echo ""
  echo "Starting server on http://${APP_HOST}:${APP_PORT}"
  echo "Access from other devices: http://<tailscale-ip>:${APP_PORT}"
  echo ""
  python -m uvicorn backend.main:app --host "$APP_HOST" --port "$APP_PORT"

else
  # ── Dev: hot-reload frontend + backend separately ────────────────
  echo "Starting FastAPI backend (${APP_HOST}:${APP_PORT})..."
  python -m uvicorn backend.main:app --reload --host "$APP_HOST" --port "$APP_PORT" &
  BACKEND_PID=$!

  echo "Starting Vite frontend (0.0.0.0:5173)..."
  cd "$SCRIPT_DIR/frontend"
  if [ ! -d "node_modules" ]; then npm install; fi
  npm run dev -- --host 0.0.0.0 &
  FRONTEND_PID=$!
  cd "$SCRIPT_DIR"

  echo ""
  echo "Dev servers running:"
  echo "  Frontend -> http://localhost:5173  (or http://<tailscale-ip>:5173)"
  echo "  API docs -> http://localhost:${APP_PORT}/docs"
  echo ""
  echo "Press Ctrl+C to stop."

  trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
  wait
fi
