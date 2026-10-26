#!/usr/bin/env bash
#
# Run every test suite in the project, in one command:
#
#   1. frontend  — vitest                          (frontend/)
#   2. backend   — pytest                          (backend/)
#   3. docker    — the single-container smoke test (tests/docker_smoke_test.sh)
#
# The terminal stays short on purpose: one line per suite, the names of any
# failing tests, and a summary. The complete output of every suite replaces
# tests/test_all.log, so the full picture is always a `less tests/test_all.log`
# away, without a wall of text on every run.
#
# Usage:
#   tests/test_all.sh              # one line per suite + summary
#   tests/test_all.sh --silent     # only failures + summary (alias: --quiet)
#
# Exit code: 0 if every suite passed, 1 if any suite or test failed, 2 on a bad
# command line.

set -uo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$TESTS_DIR/.." && pwd)"
LOG="$TESTS_DIR/test_all.log"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

usage() {
  cat <<'EOF'
Usage: tests/test_all.sh [--silent]

Runs the frontend, backend and docker test suites in order and prints a summary.
Full output is written to tests/test_all.log (replaced each run).

  --silent, --quiet   print only failures and the final summary
  -h, --help          show this help
EOF
}

SILENT=0
for arg in "$@"; do
  case "$arg" in
    -s|--silent|--quiet|-q) SILENT=1 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n\n' "$arg" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -t 1 ]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_BOLD=''; C_DIM=''; C_OFF=''
fi

# A virtualenv is optional here: the Docker suite does not use it, and CI may
# have installed the backend dependencies system-wide.
if [ -x "$BACKEND_DIR/venv/bin/python" ]; then
  PYTHON="$BACKEND_DIR/venv/bin/python"
else
  PYTHON="python3"
fi

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

# Keep the log free of ANSI codes even when the terminal supports colour.
export NO_COLOR=1 FORCE_COLOR=0

# --- Run state -------------------------------------------------------------

suite_names=()
suite_status=()   # passed | failed
suite_passed=()
suite_failed=()
suite_files=()
suite_kinds=()

total_passed=0
total_failed=0
failed_suites=0

# --- Helpers ---------------------------------------------------------------

# One line per suite, plus every failing test's name. The full output is in the
# log, so nothing here needs to be exhaustive.
print_suite_failures() {
  local name="$1" file="$2" kind="$3"
  local entries

  case "$kind" in
    vitest) entries="$(grep -E '^ FAIL ' "$file" | sed -E 's/^ +//')" ;;
    pytest) entries="$(grep -E '^FAILED ' "$file" | sed -E 's/^FAILED +//; s/ - .*//')" ;;
    docker) entries="$(grep -E '^  FAIL ' "$file" | sed -E 's/^ +//')" ;;
  esac

  printf '  %s%s%s\n' "$C_RED" "$name" "$C_OFF"
  if [ -n "$entries" ]; then
    printf '%s\n' "$entries" | sed 's/^/    /'
  else
    # The suite died before it could name a single test — a build failure, a
    # missing dependency. Its last lines say why.
    printf '    suite did not reach its test output; last lines:\n'
    tail -n 15 "$file" | sed 's/^/    /'
  fi
}

run_suite() {
  local name="$1" dir="$2" kind="$3" index="$4"; shift 4
  local out="$TMP_DIR/$index.out"
  local p f status

  [ "$SILENT" -eq 0 ] && printf '%s==> %-8s%s ' "$C_BOLD" "$name" "$C_OFF"

  ( cd "$dir" && "$@" ) >"$out" 2>&1
  local rc=$?

  {
    printf '\n======================================================================\n'
    printf '%s  (cd %s && %s)\n' "$name" "${dir#"$ROOT_DIR"/}" "$*"
    printf '======================================================================\n'
    cat "$out"
  } >>"$LOG"

  case "$kind" in
    docker)
      # The smoke test ends with "passed: N   failed: M".
      local counts
      counts="$(grep -E 'passed: [0-9]+' "$out" | tail -n1)"
      p="$(printf '%s' "$counts" | sed -nE 's/.*passed: ([0-9]+).*/\1/p')"
      f="$(printf '%s' "$counts" | sed -nE 's/.*failed: ([0-9]+).*/\1/p')"
      ;;
    *)
      # Both pytest and vitest end with a "... passed"/"... failed" line.
      p="$(grep -oE '[0-9]+ passed' "$out" | tail -n1 | grep -oE '[0-9]+')"
      f="$(grep -oE '[0-9]+ failed' "$out" | tail -n1 | grep -oE '[0-9]+')"
      ;;
  esac
  p="${p:-0}"; f="${f:-0}"

  status=passed
  [ "$rc" -eq 0 ] || status=failed

  suite_names+=("$name"); suite_status+=("$status")
  suite_passed+=("$p"); suite_failed+=("$f")
  suite_files+=("$out"); suite_kinds+=("$kind")

  total_passed=$((total_passed + p))
  total_failed=$((total_failed + f))
  [ "$status" = failed ] && failed_suites=$((failed_suites + 1))

  if [ "$SILENT" -eq 0 ]; then
    if [ "$status" = passed ]; then
      printf '%spassed%s  (%s tests)\n' "$C_GREEN" "$C_OFF" "$p"
    else
      printf '%sfailed%s  (%s passed, %s failed)\n' "$C_RED" "$C_OFF" "$p" "$f"
      print_suite_failures "$name" "$out" "$kind"
    fi
  fi
}

# --- Log header ------------------------------------------------------------

{
  printf 'Marea Alta — full test log\n'
  printf 'started: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'command: %s%s\n' "$0" "${1:+ $1}"
  printf 'note:    replaced on every run; it holds only the most recent output.\n'
} >"$LOG"

# --- Suites ----------------------------------------------------------------

# In --silent the first thing on screen is the summary (or a failure): the run
# can take several minutes, and the point of the flag is not to narrate it.
[ "$SILENT" -eq 0 ] && \
  printf '%sMarea Alta — running frontend, backend and docker tests%s\n' "$C_BOLD" "$C_OFF"

run_suite frontend "$FRONTEND_DIR" vitest 0 npm test
run_suite backend  "$BACKEND_DIR"  pytest 1 "$PYTHON" -m pytest tests/ -q -rf
run_suite docker   "$ROOT_DIR"     docker 2 "$TESTS_DIR/docker_smoke_test.sh"

# --- Summary ---------------------------------------------------------------

{
  printf '\n======================================================================\n'
  printf 'summary\n'
  printf '======================================================================\n'
} >>"$LOG"

printf '\n%s--- Summary ---------------------------------------------------------%s\n' "$C_BOLD" "$C_OFF"

i=0
while [ "$i" -lt "${#suite_names[@]}" ]; do
  if [ "${suite_status[$i]}" = passed ]; then
    line="$(printf '%-9s passed  %s tests' "${suite_names[$i]}" "${suite_passed[$i]}")"
  else
    line="$(printf '%-9s FAILED  %s passed, %s failed' "${suite_names[$i]}" "${suite_passed[$i]}" "${suite_failed[$i]}")"
  fi
  printf '  %s\n' "$line"
  printf '%s\n' "$line" >>"$LOG"
  i=$((i + 1))
done

printf '  total: %s passed, %s failed\n' "$total_passed" "$total_failed"
printf '  log:   %s\n' "${LOG#"$ROOT_DIR"/}"
{
  printf 'total: %s passed, %s failed\n' "$total_passed" "$total_failed"
  printf 'log: %s\n' "$LOG"
} >>"$LOG"

# In --silent the failures have not been printed yet; this is where they appear.
if [ "$SILENT" -eq 1 ] && [ "$failed_suites" -gt 0 ]; then
  printf '\n%s--- Failures -------------------------------------------------------%s\n' "$C_BOLD" "$C_OFF"
  i=0
  while [ "$i" -lt "${#suite_names[@]}" ]; do
    if [ "${suite_status[$i]}" = failed ]; then
      print_suite_failures "${suite_names[$i]}" "${suite_files[$i]}" "${suite_kinds[$i]}"
    fi
    i=$((i + 1))
  done
fi

printf '%s\n' "---------------------------------------------------------------------"

if [ "$failed_suites" -eq 0 ]; then
  printf '%sAll suites passed.%s  (%s tests, full log: %s)\n' \
    "$C_GREEN" "$C_OFF" "$total_passed" "${LOG#"$ROOT_DIR"/}"
  printf 'ALL SUITES PASSED\n' >>"$LOG"
  exit 0
fi

printf '%s%s suite(s) failed.%s  Full log: %s\n' \
  "$C_RED" "$failed_suites" "$C_OFF" "${LOG#"$ROOT_DIR"/}"
printf 'RESULT: FAILED (%s suite(s))\n' "$failed_suites" >>"$LOG"
exit 1
