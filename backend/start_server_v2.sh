#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

export PYTHONPATH="$PROJECT_ROOT"

PORT=${SERVER_V2_PORT:-8200}

# If already running on port, do not start a duplicate
if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "Server v0.2 already running on port $PORT"
  exit 0
fi

exec uvicorn backend.v0_2.server.app:app --host 127.0.0.1 --port "$PORT"


