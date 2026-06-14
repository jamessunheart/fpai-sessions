#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCRIPT="$REPO_ROOT/tools/proof/log_proof.sh"

passed=0
failed=0

pass() {
  passed=$((passed + 1))
}

fail() {
  failed=$((failed + 1))
  echo "FAIL: $1"
}

assert_eq() {
  local want="$1"
  local got="$2"
  local label="$3"
  if [[ "$want" == "$got" ]]; then
    pass
  else
    fail "$label (want '$want', got '$got')"
  fi
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

registry="$tmpdir/REGISTRY.json"
proof_log="$tmpdir/PROOF_LOG.md"

cat >"$registry" <<'JSON'
{
  "schema": "build-registry.v1",
  "active_builds": [
    {
      "id": "build-test-merged",
      "branch": "build/SPEC_test",
      "status": "merged",
      "spec": "core/BUILD/specs/SPEC_test.md"
    },
    {
      "id": "build-test-building",
      "branch": "build/SPEC_building",
      "status": "building",
      "spec": "core/BUILD/specs/SPEC_building.md"
    }
  ]
}
JSON

first_output="$(PROOF_REGISTRY="$registry" PROOF_LOG="$proof_log" bash "$SCRIPT" 2>&1)"
first_count="$(grep -c 'build-test-merged' "$proof_log" 2>/dev/null || true)"
building_count="$(grep -c 'build-test-building' "$proof_log" 2>/dev/null || true)"

assert_eq "1" "$first_count" "first run appends merged build once"
assert_eq "0" "$building_count" "first run skips non-merged build"
if [[ "$first_output" == *"Logged 1 new proof entry"* ]]; then
  pass
else
  fail "first run reports one logged entry"
fi

second_output="$(PROOF_REGISTRY="$registry" PROOF_LOG="$proof_log" bash "$SCRIPT" 2>&1)"
second_count="$(grep -c 'build-test-merged' "$proof_log" 2>/dev/null || true)"

assert_eq "1" "$second_count" "second run keeps a single merged entry"
if [[ "$second_output" == *"Logged 0 new proof entries"* ]]; then
  pass
else
  fail "second run reports zero logged entries"
fi

echo "RESULT: $passed passed, $failed failed"
if [[ "$failed" -ne 0 ]]; then
  exit 1
fi
