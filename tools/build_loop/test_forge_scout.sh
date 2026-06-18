#!/usr/bin/env bash
# Smoke tests for the pre-build Forge scout.
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$REPO_ROOT/tools/build_loop/forge_scout.sh"
ORCH="$REPO_ROOT/tools/build_loop/build_orchestrator.sh"
PASSED=0
FAILED=0

pass() { PASSED=$((PASSED + 1)); }
fail() {
  FAILED=$((FAILED + 1))
  echo "FAIL: $1"
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/fpai-forge-scout-test.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

SPEC="$TMP/SPEC_test.md"
LOG="$TMP/scout_log.jsonl"
FAKE="$TMP/fake_forge.sh"

cat > "$SPEC" <<'EOF'
# SPEC_test

Build a small model router helper.
EOF

cat > "$FAKE" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
cat <<'OUT'
EXISTING: core/STATE/AVAILABLE_RESOURCES.md lists git and Python packages that should be checked before adding dependencies.
LIBRARY: LiteLLM Proxy
BEST_PRACTICE: Reuse a provider-router library behind the Resource Discipline Gate instead of hand-coding every provider.
SAVE: 2-4 hours by drafting an adoption spec instead of a fresh router.
OUT
EOF
chmod +x "$FAKE"

FORGE_SCOUT_CMD="$FAKE" FORGE_SCOUT_LOG="$LOG" bash "$SCRIPT" "$SPEC" >/tmp/forge_scout_test.out 2>&1
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  pass
else
  fail "forge_scout.sh should exit 0"
  cat /tmp/forge_scout_test.out
fi

if grep -Fq "## Forge Scout Report" "$SPEC" && grep -Fq "LiteLLM Proxy" "$SPEC"; then
  pass
else
  fail "spec should receive Forge Scout Report with library finding"
  cat "$SPEC"
fi

if python3 - "$LOG" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]
assert rows[-1]["spec_id"] == "SPEC_test"
assert rows[-1]["existing_found"] is True
assert rows[-1]["library_found"] is True
assert "2-4 hours" in rows[-1]["estimated_time_saved"]
PY
then
  pass
else
  fail "scout_log.jsonl should record existing/library/time-saved fields"
  cat "$LOG" 2>/dev/null || true
fi

before="$(wc -l < "$SPEC")"
FORGE_SCOUT_CMD="$FAKE" FORGE_SCOUT_LOG="$LOG" bash "$SCRIPT" "$SPEC" >/tmp/forge_scout_test.out 2>&1
after="$(wc -l < "$SPEC")"
if [ "$before" = "$after" ]; then
  pass
else
  fail "forge_scout.sh should not append duplicate reports"
fi

DISABLED_SPEC="$TMP/SPEC_disabled.md"
printf '# SPEC_disabled\n' > "$DISABLED_SPEC"
FORGE_SCOUT_DISABLE=1 FORGE_SCOUT_CMD="$FAKE" FORGE_SCOUT_LOG="$LOG" bash "$SCRIPT" "$DISABLED_SPEC" >/tmp/forge_scout_test.out 2>&1
if ! grep -Fq "Forge Scout Report" "$DISABLED_SPEC"; then
  pass
else
  fail "FORGE_SCOUT_DISABLE should skip append"
fi

scout_line="$(grep -n 'forge_scout.sh' "$ORCH" | head -1 | cut -d: -f1)"
codex_line="$(grep -n 'run_codex.sh' "$ORCH" | tail -1 | cut -d: -f1)"
if [ -n "$scout_line" ] && [ -n "$codex_line" ] && [ "$scout_line" -lt "$codex_line" ]; then
  pass
else
  fail "build_orchestrator.sh should run forge_scout.sh before run_codex.sh"
fi

echo "RESULT: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
