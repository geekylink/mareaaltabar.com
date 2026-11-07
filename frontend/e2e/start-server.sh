#!/usr/bin/env bash
# Start FastAPI against a throwaway database for the Playwright suite.
#
# Never touches backend/data/ or backend/.env: every value is an absolute path
# under frontend/e2e/.tmp, deleted at the start of each run. The admin account is
# disposable and only exists in that database.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$(cd "$HERE/.." && pwd)"
ROOT="$(cd "$FRONTEND/.." && pwd)"
BACKEND="$ROOT/backend"
TMP="$FRONTEND/e2e/.tmp"
PORT="${E2E_PORT:-8010}"
PYTHON="${PYTHON:-python3}"

rm -rf "$TMP"
mkdir -p "$TMP/uploads"

export ENVIRONMENT=development
export COOKIE_SECURE=false
export DAILY_LOG_PURGE=false
export DATABASE_PATH="$TMP/e2e.db"
export UPLOAD_DIR="$TMP/uploads"

cd "$BACKEND"

# Creates the tables and the admin; importing app.main then seeds the weekly
# schedule, the drinks menu and the launch post into the empty database.
"$PYTHON" manage_admin.py create e2e --password e2e-test-pass

exec "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
