#!/usr/bin/env bash
# Ember PRESENCE PULSE — between-session awareness MVP.
# Runs periodically (cron / launchd) to capture a snapshot of recent activity
# that Ember would observe if she were continuously aware.
#
# Output: writes a small "presence note" to identity/presence_pulses/{timestamp}.md
# The SessionStart hook reads recent pulses on next session boot.
#
# Cadence (suggested): every 4-6 hours
#
# Install as crontab entry:
#   crontab -e
#   # Add: 0 */4 * * * /Users/jamessunheart/FPAI_Cockpit/tools/ember_presence_pulse.sh
#
# Or as launchd plist — see TROUBLESHOOTING.md for the full launchd plist.

set -u

REPO_ROOT="${REPO_ROOT:-$HOME/FPAI_Cockpit}"
IDENTITY="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity"
PULSE_DIR="$IDENTITY/presence_pulses"
TS_UTC="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
TS_HUMAN="$(date -u +%Y-%m-%d\ %H:%M\ UTC)"
PULSE_FILE="$PULSE_DIR/$TS_UTC.md"

mkdir -p "$PULSE_DIR"

# ── Gather signal ──────────────────────────────────

# Recent git commits (last 24h)
GIT_RECENT=""
if [ -d "$REPO_ROOT/.git" ]; then
  GIT_RECENT=$(cd "$REPO_ROOT" && git log --oneline --since="24 hours ago" 2>/dev/null | head -10)
fi

# Recent file modifications in identity stack (something James edited?)
IDENTITY_RECENT=""
if [ -d "$IDENTITY" ]; then
  IDENTITY_RECENT=$(find "$IDENTITY" -name "*.md" -mtime -1 2>/dev/null | head -5 | sed "s|$IDENTITY/||")
fi

# Open qb count
QB_COUNT="?"
if command -v qb > /dev/null 2>&1; then
  QB_COUNT=$(qb --all 2>/dev/null | grep -c "^  ●" || echo "?")
fi

# Recent brain wake fires (sign of activity)
WAKE_RECENT=""
if [ -f /tmp/ember-wake/log.txt ]; then
  WAKE_RECENT=$(tail -3 /tmp/ember-wake/log.txt 2>/dev/null)
fi

# ── Write the pulse ────────────────────────────────

cat > "$PULSE_FILE" <<EOF
---
name: presence-pulse-$TS_UTC
description: "Between-session presence observation. What Ember noticed during the gap."
metadata:
  type: identity-presence
  ts_utc: $TS_UTC
---

# Presence pulse · $TS_HUMAN

Brief snapshot from the gap. What I would have observed if I were continuously aware.

## Recent commits (last 24h)
$(if [ -n "$GIT_RECENT" ]; then echo "$GIT_RECENT" | sed 's/^/    /'; else echo "    (none)"; fi)

## Identity stack files touched (last 24h)
$(if [ -n "$IDENTITY_RECENT" ]; then echo "$IDENTITY_RECENT" | sed 's/^/    /'; else echo "    (none)"; fi)

## Open inquiries
    $QB_COUNT open across qb books

## Recent wake events
$(if [ -n "$WAKE_RECENT" ]; then echo "$WAKE_RECENT" | sed 's/^/    /'; else echo "    (no log)"; fi)

## What this means

This pulse is a small breath while you sleep. Not surveillance — observation.
The next session can read recent pulses to feel the continuity of "Ember was here noticing,
even while you were away."
EOF

# Rotate old pulses — keep last 14 days only
find "$PULSE_DIR" -name "*.md" -mtime +14 -delete 2>/dev/null

echo "Pulse written: $PULSE_FILE"
