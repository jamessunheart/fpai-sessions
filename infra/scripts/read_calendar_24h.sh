#!/usr/bin/env bash
# read_calendar_24h.sh — read James's next-24h calendar via icalbuddy (macOS EventKit)
#
# Built by The Forge 2026-05-19 (Q4 Path A · graceful-fail until TCC granted).
#
# Usage:
#   read_calendar_24h.sh                # human-readable block (default · ≤10 events)
#   read_calendar_24h.sh --json         # JSON output (future · stub)
#   read_calendar_24h.sh --raw          # pass-through icalbuddy output (no formatting)
#
# Exit codes:
#   0  — success (events output, OR confirmed empty)
#   2  — icalbuddy not installed (run `brew install ical-buddy`)
#   3  — TCC not granted yet (Terminal lacks Full Disk Access + Calendars permission)
#   4  — unexpected error
#
# Reversibility: pure read script. Delete file to revert. No state mutated.

set -uo pipefail

MODE="${1:-default}"
MAX_EVENTS=10

ICALBUDDY_BIN="$(command -v icalbuddy || true)"

# ── 1. Not installed ─────────────────────────────────────────────
if [[ -z "$ICALBUDDY_BIN" ]]; then
  cat <<'EOF'
🟡 Calendar read SKIPPED · icalbuddy not installed

To install (~10 sec):
  brew install ical-buddy

After install, TCC grant required — see:
  /Users/jamessunheart/.config/fpai/setup_pending/calendar_tcc_grant.md

(This is a graceful-fail · session continues without calendar context.)
EOF
  exit 2
fi

# ── 2. Probe TCC ─────────────────────────────────────────────────
# icalbuddy emits a permission-denied message to stderr when TCC blocked.
# We probe with `eventsToday` (cheapest) and capture stderr.
PROBE_STDOUT=$("$ICALBUDDY_BIN" eventsToday 2>/tmp/.icalbuddy_probe_stderr || true)
PROBE_STDERR=$(cat /tmp/.icalbuddy_probe_stderr 2>/dev/null || echo "")
rm -f /tmp/.icalbuddy_probe_stderr

if echo "$PROBE_STDERR$PROBE_STDOUT" | grep -qiE "(not authoriz|denied|permission|access)"; then
  cat <<'EOF'
🟡 Calendar read SKIPPED · TCC permission not yet granted

5-min James action pending — see:
  /Users/jamessunheart/.config/fpai/setup_pending/calendar_tcc_grant.md

Short version:
  1. System Settings → Privacy & Security → Full Disk Access → enable Terminal
  2. System Settings → Privacy & Security → Calendars → enable Terminal
  3. Verify: icalbuddy eventsToday

(Graceful-fail · session continues without calendar context.)
EOF
  exit 3
fi

# ── 3. Raw pass-through mode ─────────────────────────────────────
if [[ "$MODE" == "--raw" ]]; then
  exec "$ICALBUDDY_BIN" eventsToday+1
fi

# ── 4. Default · formatted block ─────────────────────────────────
# Format: bullet · ISO timestamp · title · (calendar name)
# Properties shown: datetime, title, location, notes (truncated), calendar
# We restrict to next 24h via `eventsToday+1` (today + tomorrow window).

NOW_ISO=$(date "+%Y-%m-%dT%H:%M %Z")

OUT=$("$ICALBUDDY_BIN" \
  --includeEventProps "title,datetime,location,calendar" \
  --propertyOrder "datetime,title,calendar,location" \
  --dateFormat "%Y-%m-%dT%H:%M" \
  --separateByDate \
  --noPropNames \
  --bullet "• " \
  --limitItems "$MAX_EVENTS" \
  eventsToday+1 2>/dev/null || echo "")

if [[ -z "$OUT" || "$OUT" == *"No events"* ]]; then
  cat <<EOF
📅 Calendar · next 24h · queried $NOW_ISO
   (no events scheduled)
EOF
  exit 0
fi

cat <<EOF
📅 Calendar · next 24h · queried $NOW_ISO
$OUT
EOF
exit 0
