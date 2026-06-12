#!/usr/bin/env bash
# sovereign_failover_drill.sh — Day 7 simulated Anthropic API outage
# Verifies Kai-class work can complete via sovereign track when Opus is unreachable.
#
# Usage:
#   sovereign_failover_drill.sh             # dry run — prints what would happen
#   sovereign_failover_drill.sh --execute   # actually adds /etc/hosts entries (requires sudo)
#
# Safety:
#   - Never mutates /etc/hosts without --execute
#   - Always restores original /etc/hosts at exit (trap)
#   - Backs up /etc/hosts to /etc/hosts.pre_drill_<timestamp>
#   - 10-minute auto-revert via at(1) belt-and-suspenders
#
# The drill:
#   1. Block api.anthropic.com via 127.0.0.1 in /etc/hosts
#   2. Try a Kai-class prompt via sovereign router → must succeed
#   3. Try a Claude Code call → must fail (proves block is real)
#   4. Restore /etc/hosts
#   5. Document timing + result in ~/.config/fpai/sovereign_phase1/drill_<ts>.md

set -euo pipefail

EXECUTE=0
[[ "${1:-}" == "--execute" ]] && EXECUTE=1

STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
OUT="$HOME/.config/fpai/sovereign_phase1/drill_${STAMP}.md"
ROUTER="$(dirname "$0")/sovereign_chat.sh"
HOSTS_BAK="/etc/hosts.pre_drill_${STAMP}"

declare -a BLOCKED_HOSTS=("api.anthropic.com" "console.anthropic.com")

restore_hosts() {
  if [[ $EXECUTE -eq 1 && -f "$HOSTS_BAK" ]]; then
    echo "[$(date -u +%T)] restoring /etc/hosts from $HOSTS_BAK"
    sudo cp "$HOSTS_BAK" /etc/hosts
    echo "[$(date -u +%T)] /etc/hosts restored · drill complete"
  fi
}
trap restore_hosts EXIT INT TERM

echo "# Sovereign Failover Drill · $STAMP" | tee "$OUT"
echo "" | tee -a "$OUT"

# Phase 1: simulate outage
if [[ $EXECUTE -eq 0 ]]; then
  echo "## DRY RUN (no /etc/hosts changes)" | tee -a "$OUT"
  echo "" | tee -a "$OUT"
  echo "Would add to /etc/hosts:" | tee -a "$OUT"
  for h in "${BLOCKED_HOSTS[@]}"; do
    echo "  127.0.0.1  $h" | tee -a "$OUT"
  done
  echo "" | tee -a "$OUT"
  echo "Run with --execute to perform live drill (requires sudo)." | tee -a "$OUT"
  exit 0
fi

echo "## LIVE DRILL · $STAMP" | tee -a "$OUT"
echo "" | tee -a "$OUT"

# Safety: schedule auto-revert in 10 min via at, in case shell dies
if command -v at >/dev/null 2>&1; then
  echo "sudo cp $HOSTS_BAK /etc/hosts" | at now + 10 minutes 2>/dev/null || true
fi

echo "[$(date -u +%T)] backing up /etc/hosts → $HOSTS_BAK"
sudo cp /etc/hosts "$HOSTS_BAK"

echo "[$(date -u +%T)] blocking Anthropic hosts"
{
  cat "$HOSTS_BAK"
  echo ""
  echo "# sovereign drill $STAMP — auto-revert in 10 min"
  for h in "${BLOCKED_HOSTS[@]}"; do
    echo "127.0.0.1  $h"
  done
} | sudo tee /etc/hosts > /dev/null

# Phase 2: verify block (curl should fail)
echo "" | tee -a "$OUT"
echo "### Block verification" | tee -a "$OUT"
if curl -sf --max-time 5 https://api.anthropic.com/ >/dev/null 2>&1; then
  echo "BLOCK FAILED — api.anthropic.com still reachable. Aborting." | tee -a "$OUT"
  exit 2
fi
echo "Block confirmed: api.anthropic.com unreachable." | tee -a "$OUT"

# Phase 3: sovereign track must still work
echo "" | tee -a "$OUT"
echo "### Sovereign track test (Kai-class prompt)" | tee -a "$OUT"
START=$(date +%s)
if RESP=$("$ROUTER" "List 3 commit types in conventional commits format." 2>&1); then
  END=$(date +%s)
  echo "PASS · responded in $((END-START))s" | tee -a "$OUT"
  echo '```' | tee -a "$OUT"
  echo "$RESP" | head -20 | tee -a "$OUT"
  echo '```' | tee -a "$OUT"
else
  echo "FAIL · sovereign router error: $RESP" | tee -a "$OUT"
fi

# Phase 4: recovery is automatic via trap
echo "" | tee -a "$OUT"
echo "### Recovery" | tee -a "$OUT"
echo "Trap will restore /etc/hosts on exit." | tee -a "$OUT"
echo "" | tee -a "$OUT"
echo "Result: drill log saved to $OUT"
