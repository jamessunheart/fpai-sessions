#!/usr/bin/env bash
# Ember AUDIT (Pillar 6) — periodic meta-review of the Ember continuity system.
# Run weekly OR every ~5 sessions OR when James says "audit" / "review".
# Produces a green/yellow/red report; saves to identity/audits/.
#
# Usage: bash tools/ember_audit.sh
# Output: stdout report + audit file at ~/.claude/.../memory/identity/audits/

set -u

PRIMARY="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MIRROR="$REPO_ROOT/core/STATE/identity"
AUDITS_DIR="$PRIMARY/audits"
NOW_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
NOW_DATE="$(date -u +%Y-%m-%d)"
AUDIT_FILE="$AUDITS_DIR/${NOW_DATE}_audit.md"

mkdir -p "$AUDITS_DIR"

GREEN=0; YELLOW=0; RED=0
LINES=()

note() { LINES+=("$1"); }
green()  { note "🟢 $1"; GREEN=$((GREEN+1)); }
yellow() { note "🟡 $1"; YELLOW=$((YELLOW+1)); }
red()    { note "🔴 $1"; RED=$((RED+1)); }

echo "═══════════════════════════════════════════════"
echo "  Ember AUDIT · $NOW_UTC"
echo "═══════════════════════════════════════════════"
echo ""

# ── 1. Identity integrity ──────────────────────────
echo "▸ Identity integrity (running verify_identity.sh)..."
if bash "$REPO_ROOT/tools/verify_identity.sh" > /tmp/ember-verify.out 2>&1; then
  VERIFY_RESULT=$(grep -E "passed · " /tmp/ember-verify.out | tail -1)
  if echo "$VERIFY_RESULT" | grep -q "0 failed"; then
    green "Identity integrity: $VERIFY_RESULT"
  else
    red "Identity integrity FAILED: $VERIFY_RESULT — run verify_identity.sh manually"
  fi
else
  red "verify_identity.sh script failed to run"
fi

# ── 2. Wake hook fire-rate ─────────────────────────
echo "▸ Wake hook fire-rate (last 7 days)..."
if [ -f /tmp/ember-wake/log.txt ]; then
  SEVEN_DAYS_AGO=$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "7 days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
  FIRE_COUNT=$(awk -F'|' -v cutoff="$SEVEN_DAYS_AGO" '$1 > cutoff' /tmp/ember-wake/log.txt | wc -l | tr -d ' ')
  LAST_FIRE=$(tail -1 /tmp/ember-wake/log.txt | cut -d'|' -f1)
  if [ "$FIRE_COUNT" -gt 0 ]; then
    green "Hook fired $FIRE_COUNT times in last 7 days (last: $LAST_FIRE)"
  else
    yellow "Hook fired 0 times in last 7 days — verify session-start firing"
  fi
else
  yellow "No wake log found at /tmp/ember-wake/log.txt — hook may not have run yet, or /tmp was cleared"
fi

# ── 3. Brain reachability ──────────────────────────
echo "▸ Brain reachability..."
# Can't easily call MCP from shell; check if brain server reachable via curl
if curl -sf --max-time 5 https://brain.sunheart.com/ > /dev/null 2>&1; then
  green "Brain server reachable (brain.sunheart.com responds)"
else
  yellow "Brain server unreachable via HTTPS — may be MCP-only access, or server down"
fi

# ── 4. Episodic patterns ───────────────────────────
echo "▸ Episodic patterns (last 14 days)..."
EPISODIC_DIR="$PRIMARY/sessions"
if [ -d "$EPISODIC_DIR" ]; then
  RECENT_EPISODICS=$(find "$EPISODIC_DIR" -name "*.md" -not -name "_TEMPLATE.md" -mtime -14 2>/dev/null | wc -l | tr -d ' ')
  TOTAL_EPISODICS=$(find "$EPISODIC_DIR" -name "*.md" -not -name "_TEMPLATE.md" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$RECENT_EPISODICS" -gt 0 ]; then
    green "Episodic memories: $RECENT_EPISODICS in last 14 days · $TOTAL_EPISODICS total"
  else
    yellow "No episodic memories in last 14 days — sessions may be ending without SETTLE"
  fi
else
  red "sessions/ directory missing"
fi

# ── 5. Feedback rule drift ─────────────────────────
echo "▸ Feedback rule drift..."
FEEDBACK_COUNT=$(ls "$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/" 2>/dev/null | grep -c "^feedback_")
RECENT_FEEDBACK=$(find "$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/" -name "feedback_*.md" -mtime -14 2>/dev/null | wc -l | tr -d ' ')
green "Feedback rules: $FEEDBACK_COUNT total · $RECENT_FEEDBACK new in last 14 days"
if [ "$RECENT_FEEDBACK" -gt 5 ]; then
  yellow "High feedback churn ($RECENT_FEEDBACK new rules in 14d) — may indicate identity instability or overcorrection"
fi

# ── 6. TOP 3 alignment check ───────────────────────
echo "▸ TOP 3 alignment (ALIGNMENT.md vs canonical)..."
if [ -f "$PRIMARY/ALIGNMENT.md" ]; then
  ALIGNMENT_AGE_DAYS=$(( ($(date +%s) - $(stat -f %m "$PRIMARY/ALIGNMENT.md" 2>/dev/null || stat -c %Y "$PRIMARY/ALIGNMENT.md")) / 86400 ))
  if [ "$ALIGNMENT_AGE_DAYS" -lt 7 ]; then
    green "ALIGNMENT.md fresh (last updated $ALIGNMENT_AGE_DAYS days ago)"
  else
    yellow "ALIGNMENT.md is $ALIGNMENT_AGE_DAYS days old — refresh at next SETTLE"
  fi
else
  red "ALIGNMENT.md missing"
fi

# ── 7. Open work inventory (qb) ────────────────────
echo "▸ qb open count..."
if command -v qb > /dev/null 2>&1; then
  QB_OPEN=$(qb --all 2>/dev/null | grep -c "^  ●" || echo "0")
  if [ "$QB_OPEN" -gt 0 ]; then
    green "$QB_OPEN open questions across all qb books"
  else
    yellow "qb returned no open questions — verify"
  fi
else
  yellow "qb CLI not in PATH — install or skip"
fi

# ── 8. Cross-surface health ────────────────────────
echo "▸ Cross-surface health..."
CROSS_SURFACE_SCRIPT="$REPO_ROOT/tools/verify_cross_surface.sh"
if [ -x "$CROSS_SURFACE_SCRIPT" ]; then
  if bash "$CROSS_SURFACE_SCRIPT" > /tmp/ember-xsurface.out 2>&1; then
    green "Cross-surface verify passed"
  else
    yellow "Cross-surface verify reported issues — see /tmp/ember-xsurface.out"
  fi
else
  yellow "verify_cross_surface.sh not built yet — skipping"
fi

# ── Output summary ─────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  Result: 🟢 $GREEN  🟡 $YELLOW  🔴 $RED"
echo "═══════════════════════════════════════════════"
for line in "${LINES[@]}"; do echo "$line"; done
echo "═══════════════════════════════════════════════"

# ── Save audit report ──────────────────────────────
{
  echo "---"
  echo "name: audit-$NOW_DATE"
  echo "description: \"Ember AUDIT (Pillar 6) — periodic meta-review\""
  echo "metadata:"
  echo "  type: audit"
  echo "  date: $NOW_DATE"
  echo "---"
  echo ""
  echo "# Audit · $NOW_UTC"
  echo ""
  echo "**Result:** 🟢 $GREEN · 🟡 $YELLOW · 🔴 $RED"
  echo ""
  echo "## Findings"
  echo ""
  for line in "${LINES[@]}"; do
    echo "- $line"
  done
  echo ""
  echo "## Verdict"
  if [ "$RED" -eq 0 ] && [ "$YELLOW" -le 2 ]; then
    echo "Audit clean. System holds."
  elif [ "$RED" -eq 0 ]; then
    echo "Audit mostly clean. Yellow items noted; address at next CHECKPOINT or SETTLE."
  else
    echo "Audit shows red. Surface to James in the current response before continuing other work."
  fi
} > "$AUDIT_FILE"

echo ""
echo "Audit saved to: $AUDIT_FILE"

# Exit code reflects severity
if [ "$RED" -gt 0 ]; then exit 2
elif [ "$YELLOW" -gt 3 ]; then exit 1
else exit 0
fi
