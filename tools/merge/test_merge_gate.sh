#!/usr/bin/env bash
# Tests for the merge gate. Uses a temp registry + the current (existing) branch
# so we exercise the registry-status logic without creating throwaway branches.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GATE="$ROOT/tools/merge/merge_gate.sh"
BR="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
TMP="$(mktemp)"
PASS=0; FAIL=0

check() { # desc, expected_exit, actual_exit, needle, output
  local desc="$1" exp="$2" act="$3" needle="$4" out="$5"
  if [ "$exp" = "$act" ] && echo "$out" | grep -q "$needle"; then
    echo "  ✓ $desc"; PASS=$((PASS+1))
  else
    echo "  ✗ $desc (exit exp=$exp act=$act; wanted '$needle')"; echo "$out" | sed 's/^/      /'; FAIL=$((FAIL+1))
  fi
}

echo "merge_gate tests (branch under test: $BR)"

# T1: registered done -> PASS
printf '{"active_builds":[{"branch":"%s","status":"done"}]}' "$BR" > "$TMP"
OUT=$(MERGE_GATE_REGISTRY="$TMP" bash "$GATE" "$BR" 2>&1); EXIT=$?
check "registered done -> PASS" 0 "$EXIT" "PASS:" "$OUT"

# T2: not registered -> FAIL not registered
printf '{"active_builds":[]}' > "$TMP"
OUT=$(MERGE_GATE_REGISTRY="$TMP" bash "$GATE" "$BR" 2>&1); EXIT=$?
check "not registered -> FAIL" 1 "$EXIT" "not registered" "$OUT"

# T3: status building -> FAIL still building
printf '{"active_builds":[{"branch":"%s","status":"building"}]}' "$BR" > "$TMP"
OUT=$(MERGE_GATE_REGISTRY="$TMP" bash "$GATE" "$BR" 2>&1); EXIT=$?
check "status building -> FAIL" 1 "$EXIT" "status is 'building'" "$OUT"

# T4: refuse main
OUT=$(MERGE_GATE_REGISTRY="$TMP" bash "$GATE" main 2>&1); EXIT=$?
check "refuse main -> FAIL" 1 "$EXIT" "refusing to gate" "$OUT"

# T5: nonexistent branch -> FAIL not found
OUT=$(MERGE_GATE_REGISTRY="$TMP" bash "$GATE" codex/does-not-exist-xyz 2>&1); EXIT=$?
check "nonexistent branch -> FAIL" 1 "$EXIT" "not found" "$OUT"

rm -f "$TMP"
echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
