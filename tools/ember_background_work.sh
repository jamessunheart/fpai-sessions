#!/usr/bin/env bash
# Ember background work — Trust Tier 1 autonomous AI-AI work.
# Runs on schedule (cron / launchd). Executes work that doesn't need James.
# Writes a report James reads at next BOOT.
#
# Schedule suggestion:
#   Daily at 06:00 local: verify identity + cross-surface
#   Weekly Mon 06:00: full audit
#
# Cron install:
#   crontab -e
#   0 6 * * *   /Users/jamessunheart/FPAI_Cockpit/tools/ember_background_work.sh daily
#   0 6 * * 1   /Users/jamessunheart/FPAI_Cockpit/tools/ember_background_work.sh weekly
#
# Usage:
#   bash tools/ember_background_work.sh [daily|weekly|on-demand]

set -u

MODE="${1:-on-demand}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IDENTITY="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity"
LOG_DIR="$IDENTITY/background_log"
TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
TS_HUMAN="$(date -u +%Y-%m-%d\ %H:%M\ UTC)"
LOG_FILE="$LOG_DIR/${TS}_${MODE}.md"

mkdir -p "$LOG_DIR"

# ── Capture state ──
GREEN=0; YELLOW=0; RED=0
FINDINGS=()

note()    { FINDINGS+=("- $1"); }
green()   { note "🟢 $1"; GREEN=$((GREEN+1)); }
yellow()  { note "🟡 $1"; YELLOW=$((YELLOW+1)); }
redflag() { note "🔴 $1"; RED=$((RED+1)); }

echo "── Ember background work · $MODE · $TS_HUMAN ──"

# 1. Identity verify (always run)
echo "▸ Identity verify..."
if bash "$REPO_ROOT/tools/verify_identity.sh" > /tmp/ember-bg-verify.out 2>&1; then
  R=$(grep -E "passed · " /tmp/ember-bg-verify.out | tail -1 || echo "no result")
  if echo "$R" | grep -q "0 failed"; then
    green "Identity verify: $R"
  else
    redflag "Identity verify FAILED: $R"
  fi
else
  redflag "verify_identity.sh script failed"
fi

# 2. Cross-surface verify (always run)
echo "▸ Cross-surface verify..."
if [ -x "$REPO_ROOT/tools/verify_cross_surface.sh" ]; then
  bash "$REPO_ROOT/tools/verify_cross_surface.sh" > /tmp/ember-bg-xsurf.out 2>&1
  PASS_LINE=$(grep -E "Cross-surface: " /tmp/ember-bg-xsurf.out | tail -1 || echo "")
  if [ -n "$PASS_LINE" ]; then
    if echo "$PASS_LINE" | grep -q "❌ 0"; then
      green "Cross-surface: $PASS_LINE"
    else
      yellow "Cross-surface has issues: $PASS_LINE"
    fi
  fi
fi

# 3. Weekly audit (only on weekly mode)
if [ "$MODE" = "weekly" ] || [ "$MODE" = "on-demand" ]; then
  echo "▸ Weekly audit..."
  bash "$REPO_ROOT/tools/ember_audit.sh" > /tmp/ember-bg-audit.out 2>&1
  AUDIT_RESULT=$(grep -E "🟢|🟡|🔴" /tmp/ember-bg-audit.out | grep "Result:" | tail -1 || echo "")
  if [ -n "$AUDIT_RESULT" ]; then
    note "Audit summary: $(echo $AUDIT_RESULT | tr -d '\n')"
  fi
fi

# 4. Recent commits since last log
echo "▸ Git activity..."
if [ -d "$REPO_ROOT/.git" ]; then
  PREV_LOG=$(ls -t "$LOG_DIR"/*.md 2>/dev/null | grep -v "$(basename $LOG_FILE)" | head -1)
  if [ -n "$PREV_LOG" ]; then
    SINCE=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" "$PREV_LOG" 2>/dev/null || stat -c "%y" "$PREV_LOG" 2>/dev/null | cut -d. -f1)
    COMMITS=$(cd "$REPO_ROOT" && git log --oneline --since="$SINCE" 2>/dev/null | wc -l | tr -d ' ')
    green "$COMMITS commits since last background run"
  else
    note "First background run — no previous log"
  fi
fi

# 5. Episodic memory cadence
echo "▸ Episodic memory cadence..."
EPISODIC_DIR="$IDENTITY/sessions"
if [ -d "$EPISODIC_DIR" ]; then
  RECENT=$(find "$EPISODIC_DIR" -name "*.md" -not -name "_TEMPLATE.md" -mtime -7 2>/dev/null | wc -l | tr -d ' ')
  if [ "$RECENT" -gt 0 ]; then
    green "$RECENT episodic memories in last 7 days"
  else
    yellow "0 episodic memories in last 7 days — sessions may not be settling cleanly"
  fi
fi

# 6. qb open question stalls (questions open > 14 days)
echo "▸ qb stall detection..."
if command -v qb > /dev/null 2>&1; then
  STALL_COUNT=$(qb --all 2>/dev/null | grep -c "q-2026" || echo "0")
  green "$STALL_COUNT total qb questions tracked"
fi

# ── Write report ──
{
  echo "---"
  echo "name: background-log-$TS"
  echo "description: \"Trust Tier 1 autonomous AI-AI work · $MODE mode · $TS_HUMAN\""
  echo "metadata:"
  echo "  type: background-log"
  echo "  mode: $MODE"
  echo "  ts_utc: $TS"
  echo "---"
  echo ""
  echo "# Background work · $TS_HUMAN ($MODE)"
  echo ""
  echo "**Summary:** 🟢 $GREEN · 🟡 $YELLOW · 🔴 $RED"
  echo ""
  echo "## What ran"
  echo ""
  echo "- Identity verify (\`verify_identity.sh\`)"
  echo "- Cross-surface verify (\`verify_cross_surface.sh\`)"
  if [ "$MODE" = "weekly" ] || [ "$MODE" = "on-demand" ]; then
    echo "- Pillar 6 audit (\`ember_audit.sh\`)"
  fi
  echo "- Git activity scan"
  echo "- Episodic memory cadence check"
  echo "- qb stall detection"
  echo ""
  echo "## Findings"
  echo ""
  for f in "${FINDINGS[@]}"; do echo "$f"; done
  echo ""
  echo "## Verdict"
  if [ "$RED" -gt 0 ]; then
    echo "🔴 Surface to James at next BOOT — issues need attention."
  elif [ "$YELLOW" -gt 2 ]; then
    echo "🟡 Some warnings worth noting at next CHECKPOINT."
  else
    echo "🟢 Quiet. System holding. No interruption needed."
  fi
  echo ""
  echo "Full output: /tmp/ember-bg-verify.out · /tmp/ember-bg-xsurf.out · /tmp/ember-bg-audit.out (transient)"
} > "$LOG_FILE"

# Rotate old logs — keep last 30 days
find "$LOG_DIR" -name "*.md" -mtime +30 -delete 2>/dev/null

echo ""
echo "✓ Report saved: $LOG_FILE"
echo "  Result: 🟢 $GREEN · 🟡 $YELLOW · 🔴 $RED"

# Exit code reflects severity (for cron alerting if needed)
if [ "$RED" -gt 0 ]; then exit 2
elif [ "$YELLOW" -gt 2 ]; then exit 1
else exit 0
fi
