#!/usr/bin/env bash
# Nightly SQLite backup for Marea Alta. See scripts/backup.py and
# docs/deployment.md. Kept as a shell wrapper so cron and the runbook have one
# obvious command.
set -euo pipefail

exec python3 "$(dirname "$0")/backup.py" "$@"
