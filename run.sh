#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -q -r requirements.txt

if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm ci)
fi

set -a; [ -f .env ] && . ./.env; set +a
export PAYPILOT_RP_ID="${PAYPILOT_RP_ID:-localhost}"
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT INT TERM

cd frontend
npm run dev
