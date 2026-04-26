#!/bin/bash
PORT=${FIXTURE_PORT:-18080}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cleanup() { kill "$SERVER_PID" 2>/dev/null; }
trap cleanup EXIT INT TERM
cd "$SCRIPT_DIR/site"
python3 -m http.server "$PORT" &
SERVER_PID=$!
echo "[fixture] http://127.0.0.1:$PORT/ (PID $SERVER_PID)"
wait "$SERVER_PID"