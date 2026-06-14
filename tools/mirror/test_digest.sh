#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIGEST="$ROOT/tools/mirror/digest.sh"
PASSED=0
FAILED=0

pass() {
  PASSED=$((PASSED + 1))
}

fail() {
  FAILED=$((FAILED + 1))
  echo "FAIL: $1"
}

output="$("$DIGEST" 2>&1)"
status=$?

if [ "$status" -eq 0 ]; then
  pass
else
  fail "digest.sh exited $status"
fi

for header in "## Shipped" "## In flight" "## Next"; do
  if printf '%s\n' "$output" | grep -Fq "$header"; then
    pass
  else
    fail "missing header: $header"
  fi
done

echo "RESULT: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
