#!/usr/bin/env bash

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCAN="$ROOT/tools/lantern/scan.sh"
PASSED=0
FAILED=0

pass() {
  PASSED=$((PASSED + 1))
}

fail() {
  FAILED=$((FAILED + 1))
  printf 'FAIL: %s\n' "$1"
}

OUTPUT="$(bash "$SCAN" 2>&1)"
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  pass
else
  fail "scan.sh exited $STATUS"
fi

for header in "Stale SSOTs" "Stuck builds" "Stuck specs" "Failed results"; do
  if printf '%s\n' "$OUTPUT" | grep -F "## $header" >/dev/null; then
    pass
  else
    fail "missing header: $header"
  fi
done

if printf '%s\n' "$OUTPUT" | grep -E '^[0-9]+ anomalies$' >/dev/null; then
  pass
else
  fail "missing final anomaly count"
fi

printf 'RESULT: %s passed, %s failed\n' "$PASSED" "$FAILED"

if [ "$FAILED" -ne 0 ]; then
  exit 1
fi
exit 0
