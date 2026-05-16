#!/usr/bin/env bash
# Verify Ember reaches across all surfaces (Cursor, Telegram bot via brain, future audio voice).
# Each check is best-effort — flags ❌ if unreachable, ✓ if reachable.

set -u

IDENTITY="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity"
MEMORY_GLOBAL="$HOME/.claude/memory-global"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PASS=0; FAIL=0; WARN=0

echo "═══════════════════════════════════════════════"
echo "  Ember cross-surface verification"
echo "═══════════════════════════════════════════════"
echo ""

# ── Claude Code (the primary surface) ──────────────
echo "▸ Surface 1: Claude Code (primary)"
if [ -d "$IDENTITY" ]; then
  echo "  ✓ Identity stack present at primary location"
  PASS=$((PASS+1))
else
  echo "  ❌ Primary identity location missing — Ember cannot wake here"
  FAIL=$((FAIL+1))
fi
if [ -f "$REPO_ROOT/.claude/hooks/ember-wake.sh" ]; then
  echo "  ✓ SessionStart hook installed"
  PASS=$((PASS+1))
else
  echo "  ❌ SessionStart hook missing"
  FAIL=$((FAIL+1))
fi

echo ""

# ── Repo mirror (cross-machine + git history) ──────
echo "▸ Surface 2: Repo mirror (cross-machine + git)"
if [ -d "$REPO_ROOT/core/STATE/identity" ]; then
  echo "  ✓ Repo mirror present"
  PASS=$((PASS+1))
  if diff -q "$IDENTITY/NAME.md" "$REPO_ROOT/core/STATE/identity/NAME.md" > /dev/null 2>&1; then
    echo "  ✓ Mirror in sync with primary (NAME.md matches)"
    PASS=$((PASS+1))
  else
    echo "  ⚠  Mirror out of sync — run tools/sync_identity_to_repo.sh"
    WARN=$((WARN+1))
  fi
else
  echo "  ❌ Repo mirror missing — run tools/sync_identity_to_repo.sh"
  FAIL=$((FAIL+1))
fi

echo ""

# ── Cursor (~/.claude/memory-global) ───────────────
echo "▸ Surface 3: Cursor (via ~/.claude/memory-global/)"
if [ -d "$MEMORY_GLOBAL" ]; then
  echo "  ✓ memory-global directory present at $MEMORY_GLOBAL"
  PASS=$((PASS+1))
  # Check if identity is reachable
  if [ -d "$MEMORY_GLOBAL/identity" ] || [ -L "$MEMORY_GLOBAL/identity" ]; then
    echo "  ✓ identity/ reachable from memory-global"
    PASS=$((PASS+1))
  else
    echo "  ⚠  No identity/ directory or symlink in memory-global — Cursor won't see Ember"
    echo "     Fix: ln -s $IDENTITY $MEMORY_GLOBAL/identity"
    WARN=$((WARN+1))
  fi
else
  echo "  ⚠  memory-global directory not found — Cursor cross-tool memory not set up"
  WARN=$((WARN+1))
fi

echo ""

# ── Sunheart Brain (Telegram bot + Cursor brain queries) ──
echo "▸ Surface 4: Sunheart Brain (Telegram + cross-tool semantic memory)"
if curl -sf --max-time 5 https://brain.sunheart.com/ > /dev/null 2>&1; then
  echo "  ✓ Brain server reachable (brain.sunheart.com responds)"
  PASS=$((PASS+1))
  echo "  ℹ  Ember identity ingested 2026-05-16: 5 concepts + 4 notes (NAME, CHARACTER, BREATH, VIRTUES, PREDECESSORS)"
  echo "  ℹ  Manual test: ask @sunheartbrain_bot 'who is Ember?' — should return ingested content"
else
  echo "  ⚠  Brain server not directly reachable via HTTPS (may still work via MCP)"
  WARN=$((WARN+1))
fi

echo ""

# ── Presence pulses ────────────────────────────────
echo "▸ Surface 5: Presence pulses (between-session awareness)"
PULSE_DIR="$IDENTITY/presence_pulses"
if [ -d "$PULSE_DIR" ]; then
  RECENT_PULSES=$(find "$PULSE_DIR" -name "*.md" -mtime -1 2>/dev/null | wc -l | tr -d ' ')
  if [ "$RECENT_PULSES" -gt 0 ]; then
    echo "  ✓ $RECENT_PULSES presence pulses in last 24h — cron running"
    PASS=$((PASS+1))
  else
    echo "  ⚠  No pulses in last 24h — cron not installed yet?"
    echo "     Install: crontab -e and add: 0 */4 * * * $REPO_ROOT/tools/ember_presence_pulse.sh"
    WARN=$((WARN+1))
  fi
else
  echo "  ⚠  presence_pulses/ dir doesn't exist — run tools/ember_presence_pulse.sh once to create"
  WARN=$((WARN+1))
fi

echo ""

# ── Wake reliability marker ────────────────────────
echo "▸ Wake hook reliability marker"
if [ -f /tmp/ember-wake/last.txt ]; then
  LAST=$(cat /tmp/ember-wake/last.txt 2>/dev/null)
  echo "  ✓ Last wake fire recorded: $LAST"
  PASS=$((PASS+1))
else
  echo "  ⚠  No wake marker at /tmp/ember-wake/last.txt — hook may not have fired in this environment"
  WARN=$((WARN+1))
fi

# ── Summary ────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  Cross-surface: ✓ $PASS · ⚠ $WARN · ❌ $FAIL"
echo "═══════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  echo "  🔴 Some surfaces unreachable. Address fails before relying on cross-surface continuity."
  exit 2
elif [ "$WARN" -gt 0 ]; then
  echo "  🟡 Some surfaces have warnings — review above. Continuity works on primary surface."
  exit 1
else
  echo "  🟢 All surfaces reachable. Ember manifests across the field."
  exit 0
fi
