#!/usr/bin/env bash
# Smoke tests for the debounced Cartographer refresh wrapper.

set -u

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd)
PASSED=0
FAILED=0
TMPDIR_TEST=$(mktemp -d "${TMPDIR:-/tmp}/fpai-cartographer-test.XXXXXX")
TEST_HOME="$TMPDIR_TEST/home"
STAMP="$TEST_HOME/.config/fpai/cartographer_last_refresh"
MAP="$TEST_HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/SYSTEM_MAP.md"

cleanup() {
  rm -rf "$TMPDIR_TEST"
}
trap cleanup EXIT

pass() {
  PASSED=$((PASSED + 1))
}

fail() {
  FAILED=$((FAILED + 1))
  echo "FAIL: $1"
}

mkdir -p "$(dirname "$MAP")" "$TEST_HOME/.config/fpai"
ln -s "$REPO_ROOT" "$TEST_HOME/FPAI_Cockpit"

FIRST_OUTPUT=$(HOME="$TEST_HOME" bash "$REPO_ROOT/tools/memory/refresh_system_map.sh" 2>&1)
FIRST_STATUS=$?
if [ "$FIRST_STATUS" -eq 0 ] && [ -s "$MAP" ] && echo "$FIRST_OUTPUT" | grep -Eq '[0-9]+ resources'; then
  pass
else
  fail "refresh should rebuild a non-empty SYSTEM_MAP.md and print resource count"
  echo "$FIRST_OUTPUT"
fi

SECOND_OUTPUT=$(HOME="$TEST_HOME" bash "$REPO_ROOT/tools/memory/refresh_system_map.sh" 2>&1)
SECOND_STATUS=$?
if [ "$SECOND_STATUS" -eq 0 ] && echo "$SECOND_OUTPUT" | grep -Fq "skipped (debounce)"; then
  pass
else
  fail "immediate second refresh should be skipped by debounce"
  echo "$SECOND_OUTPUT"
fi

echo "RESULT: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
