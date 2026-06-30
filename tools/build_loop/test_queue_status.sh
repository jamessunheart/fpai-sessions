#!/usr/bin/env bash
# Smoke tests for the build queue status report.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$REPO_ROOT/tools/build_loop/queue_status.sh"
PASSED=0
FAILED=0

pass() {
  PASSED=$((PASSED + 1))
}

fail() {
  FAILED=$((FAILED + 1))
  echo "FAIL: $1"
}

OUTPUT="$(bash "$SCRIPT" 2>&1)"
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  pass
else
  fail "queue_status.sh should exit 0"
  echo "$OUTPUT"
fi

for header in "Build state:" "Queued specs" "Built results" "Registry building"; do
  if echo "$OUTPUT" | grep -Fq "$header"; then
    pass
  else
    fail "output should contain header: $header"
    echo "$OUTPUT"
  fi
done

echo "RESULT: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
