#!/usr/bin/env bash
#
# Smoke test for the Marea Alta single-container deployment.
#
# Builds the image, starts it under an isolated compose project on its own port,
# and verifies the container end to end:
#
#   * the image builds
#   * exactly one container runs, with exactly one published port
#   * the database lives on the named volume
#   * the API responds (/api/schedule)
#   * / and /menu are server-rendered (DB rows are in the HTML, not just the shell)
#   * static assets are served
#   * the admin can be created, log in, and save a change
#   * that change and the admin survive a full container recreation (the
#     "upgrade" case: `down` keeps the volume, `up` reuses it)
#   * production mode hides /docs
#
# It is safe to run repeatedly: it uses its own compose project and port, and
# removes both its container and its volume unless SMOKE_KEEP=1 is set.
#
# Usage:
#   tests/docker_smoke_test.sh
#
# Env knobs:
#   COMPOSE_BIN   compose command            (default: docker-compose)
#   SMOKE_PROJECT compose project name       (default: marea_alta_smoke)
#   SMOKE_PORT    host port to publish       (default: 18080)
#   SMOKE_KEEP    1 = leave it running       (default: 0)
#
# Exit code: 0 if every check passed, 1 otherwise, 2 on a setup failure.

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_BIN="${COMPOSE_BIN:-docker-compose}"
PROJECT="${SMOKE_PROJECT:-marea_alta_smoke}"
PORT="${SMOKE_PORT:-18080}"
BASE=""
ADMIN_USER="${SMOKE_ADMIN_USER:-smokeadmin}"
ADMIN_PASS="${SMOKE_ADMIN_PASS:-smoke-$(date +%s)}"
KEEP="${SMOKE_KEEP:-0}"

TMP_DIR="$(mktemp -d)"
JAR="$TMP_DIR/cookies.txt"
BASE_URL=""

# The published host port; the container always listens on 8000.
export APP_PORT="$PORT"

pass=0
fail=0

if [ -t 1 ]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'; C_OFF=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_DIM=''; C_BOLD=''; C_OFF=''
fi

info() { printf '\n%s==> %s%s\n' "$C_BOLD" "$1" "$C_OFF"; }
ok()   { printf '  %sPASS%s %s\n' "$C_GREEN" "$C_OFF" "$1"; pass=$((pass + 1)); }
bad()  { printf '  %sFAIL%s %s\n' "$C_RED" "$C_OFF" "$1"; fail=$((fail + 1)); }
dim()  { printf '  %s%s%s\n' "$C_DIM" "$1" "$C_OFF"; }

dc() { "$COMPOSE_BIN" -p "$PROJECT" "$@"; }

# curl helpers. `code` prints the HTTP status; `get` prints the body.
code() { curl -sS -o /dev/null -w '%{http_code}' "$@"; }
get()  { curl -sS "$@"; }

cleanup() {
  if [ "$KEEP" = "1" ]; then
    printf '\n%sLeaving project "%s" running on %s (SMOKE_KEEP=1)%s\n' "$C_BOLD" "$PROJECT" "${BASE_URL:-?}" "$C_OFF"
    dim "Tear down later with: $COMPOSE_BIN -p $PROJECT down -v"
    return
  fi
  dc down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

wait_http() {
  local url="$1" tries="${2:-90}" i=0
  until curl -fsS -o /dev/null "$url" 2>/dev/null; do
    i=$((i + 1))
    [ "$i" -ge "$tries" ] && return 1
    sleep 1
  done
  return 0
}

# ---------------------------------------------------------------------------
info "Preparing a clean project"
dim "$COMPOSE_BIN -p $PROJECT down -v"
dc down -v --remove-orphans >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
info "Building the image"
if dc build >"$TMP_DIR/build.log" 2>&1; then
  ok "docker-compose build"
else
  bad "docker-compose build"
  echo "----- build log (tail) -----"
  tail -n 40 "$TMP_DIR/build.log"
  echo "-----------------------------"
  exit 2
fi

# ---------------------------------------------------------------------------
info "Starting the container"
if dc up -d >"$TMP_DIR/up.log" 2>&1; then
  ok "docker-compose up -d"
else
  bad "docker-compose up -d"
  tail -n 40 "$TMP_DIR/up.log"
  exit 2
fi

CID="$(dc ps -q web)"
if [ -z "$CID" ]; then
  bad "container is running"
  exit 2
fi

PUB="$(dc port web 8000 2>/dev/null | head -n1)"
HOST_PORT="${PUB##*:}"
BASE_URL="http://127.0.0.1:${HOST_PORT}"
dim "published at $PUB"

if wait_http "$BASE_URL/api/schedule" 90; then
  ok "app became healthy"
else
  bad "app became healthy"
  echo "----- container logs (tail) -----"
  dc logs --tail 60 web
  echo "---------------------------------"
  exit 2
fi

# ---------------------------------------------------------------------------
info "Container shape"

running="$(dc ps -q | wc -l | tr -d ' ')"
[ "$running" = "1" ] && ok "exactly one container runs" || bad "exactly one container runs (got $running)"

port_keys="$(docker inspect -f '{{range $p,$c := .NetworkSettings.Ports}}{{$p}} {{end}}' "$CID")"
nports="$(printf '%s' "$port_keys" | wc -w | tr -d ' ')"
if [ "$nports" = "1" ] && printf '%s' "$port_keys" | grep -q '8000/tcp'; then
  ok "exactly one published port (8000/tcp)"
else
  bad "exactly one published port (got: ${port_keys:-none})"
fi

if [ "$HOST_PORT" = "$PORT" ]; then
  ok "host port ${PORT} -> container 8000"
else
  bad "host port ${PORT} -> container 8000 (got ${HOST_PORT:-none})"
fi

mounts="$(docker inspect -f '{{range .Mounts}}{{.Type}}:{{.Destination}} {{end}}' "$CID")"
if printf '%s' "$mounts" | grep -q 'volume:/data'; then
  ok "a volume is mounted at /data"
else
  bad "a volume is mounted at /data (got: ${mounts:-none})"
fi

# ---------------------------------------------------------------------------
info "Public site"

if [ "$(code "$BASE_URL/")" = "200" ]; then
  ok "GET / -> 200"
else
  bad "GET / -> 200"
fi

home="$(get "$BASE_URL/")"

if printf '%s' "$home" | grep -q 'Latin Night'; then
  ok "GET / is server-rendered (seeded schedule present)"
else
  bad "GET / is server-rendered (seeded schedule missing)"
fi

if printf '%s' "$home" | grep -q '__MAREA_ALTA_DATA__'; then
  ok "GET / seeds window.__MAREA_ALTA_DATA__"
else
  bad "GET / seeds window.__MAREA_ALTA_DATA__"
fi

if [ "$(code "$BASE_URL/menu")" = "200" ]; then
  ok "GET /menu -> 200"
else
  bad "GET /menu -> 200"
fi

if get "$BASE_URL/menu" | grep -q 'Club Personal'; then
  ok "GET /menu is server-rendered (seeded menu present)"
else
  bad "GET /menu is server-rendered (seeded menu missing)"
fi

if curl -sSI "$BASE_URL/" | grep -qi '^x-frame-options: *DENY'; then
  ok "security headers are set (X-Frame-Options: DENY)"
else
  bad "security headers are set (X-Frame-Options: DENY)"
fi

if [ "$(code "$BASE_URL/docs")" = "404" ]; then
  ok "production mode hides /docs"
else
  bad "production mode hides /docs (got $(code "$BASE_URL/docs"))"
fi

asset="$(printf '%s' "$home" | grep -oE '/assets/[A-Za-z0-9._-]+\.js' | head -n1)"
if [ -n "$asset" ] && [ "$(code "$BASE_URL$asset")" = "200" ]; then
  ok "hashed asset is served ($asset)"
else
  bad "hashed asset is served (asset: ${asset:-none})"
fi

# ---------------------------------------------------------------------------
info "API"

if get "$BASE_URL/api/schedule" | jq -e 'type == "array" and length == 7' >/dev/null 2>&1; then
  ok "GET /api/schedule -> 7-day JSON array"
else
  bad "GET /api/schedule -> 7-day JSON array"
fi

# ---------------------------------------------------------------------------
info "Admin: create, log in, save"

if dc exec -T web python manage_admin.py create "$ADMIN_USER" --password="$ADMIN_PASS" 2>&1 | grep -q 'created successfully'; then
  ok "admin created inside the container"
else
  bad "admin created inside the container"
fi

login_code="$(code -c "$JAR" -X POST \
  --data-urlencode "username=$ADMIN_USER" \
  --data-urlencode "password=$ADMIN_PASS" \
  "$BASE_URL/admin/login")"
if [ "$login_code" = "303" ]; then
  ok "admin login accepted"
else
  bad "admin login accepted (got $login_code)"
fi

if [ "$(code -b "$JAR" "$BASE_URL/admin")" = "200" ]; then
  ok "authenticated /admin -> 200"
else
  bad "authenticated /admin -> 200"
fi

# CSRF token from the cookie jar (Netscape format: name is field 6, value 7).
CSRF="$(awk '$6 == "csrf_token" {print $7}' "$JAR" | tail -n1)"
NEW_TITLE="Smoke Test $(date +%s)"

if [ -n "$CSRF" ]; then
  save_code="$(code -b "$JAR" -X PUT \
    -H "X-CSRF-Token: $CSRF" \
    -H 'Content-Type: application/json' \
    -d "{\"title_en\":\"$NEW_TITLE\",\"title_es\":\"Prueba\",\"note_en\":\"\",\"note_es\":\"\",\"open_time\":\"16:00\",\"close_time\":\"02:00\",\"is_closed\":false}" \
    "$BASE_URL/api/schedule/0")"
  if [ "$save_code" = "200" ]; then
    ok "admin saved a schedule change (PUT /api/schedule/0)"
  else
    bad "admin saved a schedule change (got $save_code)"
  fi
else
  bad "CSRF token captured from login"
fi

saved="$(get "$BASE_URL/api/schedule" | jq -r '.[] | select(.day == 0) | .title_en')"
if [ "$saved" = "$NEW_TITLE" ]; then
  ok "the change is visible on the public API"
else
  bad "the change is visible on the public API (got: ${saved:-none})"
fi

# ---------------------------------------------------------------------------
info "Persistence across a container recreation (the upgrade case)"

db_inside="$(dc exec -T web sh -c 'test -f /data/marea_alta.db && echo yes' 2>/dev/null | tr -d '\r')"
if [ "$db_inside" = "yes" ]; then
  ok "SQLite file lives at /data/marea_alta.db"
else
  bad "SQLite file lives at /data/marea_alta.db"
fi

dc down >/dev/null 2>&1 || true   # keeps the named volume
dc up -d >/dev/null 2>&1 || true
if wait_http "$BASE_URL/api/schedule" 90; then
  ok "app came back up after recreation"
else
  bad "app came back up after recreation"
  dc logs --tail 60 web
fi

persisted="$(get "$BASE_URL/api/schedule" | jq -r '.[] | select(.day == 0) | .title_en' 2>/dev/null)"
if [ "$persisted" = "$NEW_TITLE" ]; then
  ok "the saved change survived recreation"
else
  bad "the saved change survived recreation (got: ${persisted:-none})"
fi

relogin_code="$(code -c "$JAR" -X POST \
  --data-urlencode "username=$ADMIN_USER" \
  --data-urlencode "password=$ADMIN_PASS" \
  "$BASE_URL/admin/login")"
if [ "$relogin_code" = "303" ]; then
  ok "the admin account survived recreation"
else
  bad "the admin account survived recreation (got $relogin_code)"
fi

# ---------------------------------------------------------------------------
info "Summary"
printf '  passed: %s   failed: %s\n' "$pass" "$fail"

if [ "$fail" -eq 0 ]; then
  printf '\n%sAll checks passed.%s\n' "$C_GREEN" "$C_OFF"
  exit 0
else
  printf '\n%s%s check(s) failed.%s\n' "$C_RED" "$fail" "$C_OFF"
  exit 1
fi
