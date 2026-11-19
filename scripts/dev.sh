#!/usr/bin/env sh
# Start backend (8000) and frontend (5173) together on Linux/macOS. Ctrl+C stops both.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$ROOT/backend" && uv run uvicorn app.main:create_app --factory --reload --no-access-log) &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT INT TERM
(cd "$ROOT/frontend" && npm run dev)
