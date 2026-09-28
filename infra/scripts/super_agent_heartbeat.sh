#!/usr/bin/env bash
# THE SUPER AGENT's heartbeat. Cron-run. Each beat: wake, read state, solve or spawn, log.
# Kill switch: touch ~/.config/fpai/SUPER_AGENT_DISABLE
set -uo pipefail
[ -f "$HOME/.config/fpai/SUPER_AGENT_DISABLE" ] && exit 0

REPO="$HOME/FullPotentialOS"
LOG="$REPO/core/SUPER/agent/HEARTBEAT_LOG.md"
MISSED_BEAT_ALERT_PAUSE_FILE="$HOME/.config/fpai/super_agent/missed_beat_alerts.disabled"
MISSED_BEAT_DETECTION_LOG="$HOME/.cache/super_agent/missed_beat_detections.log"
BEATS_MISSED=""

if [ "${1:-}" = "--missed-beat-alert-status" ]; then
  if [ -f "$MISSED_BEAT_ALERT_PAUSE_FILE" ]; then
    printf 'missed_beat_alerts=paused\npause_file=%s\n' "$MISSED_BEAT_ALERT_PAUSE_FILE"
  else
    printf 'missed_beat_alerts=active\npause_file=%s\n' "$MISSED_BEAT_ALERT_PAUSE_FILE"
  fi
  exit 0
fi

STAMP=$(date -u +"%Y-%m-%dT%H:%MZ")

cd "$REPO" || exit 1

# EVIDENCE SYNC (added 2026-09-03 by Claude, Super Agent cycle): the vendor bot's live log
# lives at /opt/VENDOR_LOG.md on 198. Nothing pulled it back, so the repo's evidence file
# silently fell behind what the currency actually promised a real person. Read-only mirror.
VLOG="$REPO/core/SUPER/VENDOR_LOG_198.md"
PREV="$HOME/.cache/super_agent/vendor_log_198.prev"
mkdir -p "$(dirname "$PREV")" 2>/dev/null || true
VTMP=$(mktemp)
DTMP=$(mktemp)
MIRROR_OK=yes
VENDOR_CHANGED=no
VENDOR_DELTA=""
if timeout 30 ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
     root@198.54.123.234 'cat /opt/VENDOR_LOG.md' > "$VTMP" 2>/dev/null && [ -s "$VTMP" ]; then
  { printf '# MIRROR (read-only) of /opt/VENDOR_LOG.md on 198 — pulled %s by the heartbeat.\n' "$STAMP"
    printf '# The bot log on 198 is the original. This copy exists so the repo, the steward and any\n'
    printf '# future agent can see what the Super Agent actually said to a provider. Do not edit.\n\n'
    cat "$VTMP"; } > "$VLOG"
  # DELTA WATCH (added 2026-09-03 by Claude): mirroring is not watching. Before this, a beat
  # could pull a log containing a provider's reply and still Telegram a calm 🫀 — because only
  # the model read the file, and the model may be logged out. This compares body-to-body and
  # raises the alarm in plain bash, so the one event the Build turns on cannot pass unseen.
  if [ -f "$PREV" ]; then
    if ! cmp -s "$PREV" "$VTMP"; then
      VENDOR_CHANGED=yes
      diff "$PREV" "$VTMP" 2>/dev/null | grep '^>' | sed 's/^> //' | head -c 700 > "$DTMP" || true
      VENDOR_DELTA=$(cat "$DTMP")
    fi
  fi
  cp "$VTMP" "$PREV" 2>/dev/null || true
else
  MIRROR_OK=no
  printf '\n<!-- %s: mirror pull failed (198 unreachable or log empty); last good copy kept -->\n' "$STAMP" >> "$VLOG" 2>/dev/null || true
fi
rm -f "$VTMP" "$DTMP"
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN  # stale env keys override claude.ai login → 401
"$HOME/.local/bin/claude" -p --permission-mode acceptEdits --max-turns 30 "You are THE SUPER AGENT waking on heartbeat $STAMP. Read core/SUPER/agent/SUPER_AGENT.md (your identity + law), core/SUPER/NBM.md, core/SUPER/BUILD_001.md, core/SUPER/STEWARD_LOG.md. Then: for every AI-tier item in the NBM queue, either SOLVE it now, SPAWN/prepare the thing that solves it, or name the exact reality-gate that blocks it (a human reply, a weekend, a law — not a missing habit). Never release funds, never message new external parties, never exceed a Card's bounds. Every beat, dispatch the super-steward subagent to append its scheduled release-condition verdict on the active Build to core/SUPER/STEWARD_LOG.md (this IS NBM #9 — steward on a schedule). Append one dated entry to core/SUPER/agent/HEARTBEAT_LOG.md: what you solved, what you spawned, what reality gates. Honor the falsifier in your identity file." >> "$REPO/core/SUPER/agent/heartbeat_stdout.log" 2>&1

CLAUDE_RC=$?

# BRAIN-OFFLINE DETECTOR (added 2026-09-03 by Claude, Super Agent cycle).
# Rule: a beat that could not THINK must never look like a beat that found nothing.
# On 2026-09-03T18:15Z the CLI lost its claude.ai login; the beat logged the neutral
# "agent left no entry" and Telegrammed a normal-looking heartbeat, so the standing order
# to watch /opt/VENDOR_LOG.md for La Cocinona's reply silently stopped running.
BRAIN_OK=yes
AUTH_ERR=$(tail -30 "$REPO/core/SUPER/agent/heartbeat_stdout.log" 2>/dev/null | grep -iE "not logged in|please run /login|api key|401|authenticate|ANTHROPIC_" | tail -5)
[ -z "$AUTH_ERR" ] && AUTH_ERR="(no auth error text captured; rc alone triggered this)"
if [ "$CLAUDE_RC" -ne 0 ] || tail -30 "$REPO/core/SUPER/agent/heartbeat_stdout.log" 2>/dev/null | grep -qiE "not logged in|please run /login|api key is invalid|401"; then
  BRAIN_OK=no
  printf '\n## %s — BRAIN OFFLINE\n- `claude -p` could not authenticate (rc=%s). Nothing was read, no steward verdict was appended, /opt/VENDOR_LOG.md was NOT interpreted.\n- The delta watch below still runs; the Super Agent is not READING while this holds.\n- Verbatim auth error from the CLI (do not guess the cause from this line alone):\n```\n%s\n```\n- Known causes, in the order they actually happened here:\n  1. A stale ANTHROPIC_API_KEY/AUTH_TOKEN in cron`s env overriding the claude.ai login (401 invalid key). FIXED in this script 2026-09-03 21:08 — if this recurs, the unset above is not reaching the CLI.\n  2. cron runs outside the GUI login session and cannot unlock the macOS Keychain where the OAuth credentials live. UNPROVEN. Test: run this script by hand in Terminal; if it works there and fails from cron, this is it, and the fix is a LaunchAgent (runs in the user session), not another /login.\n- FIX (James, ~1 min, tries the cheap one first): open Terminal on this Mac, run `claude`, then `/login`.\n' "$STAMP" "$CLAUDE_RC" "$AUTH_ERR" >> "$LOG"
fi
if [ "$MIRROR_OK" = "no" ]; then
  printf '\n## %s — EVIDENCE MIRROR DOWN: could not read /opt/VENDOR_LOG.md on 198. The repo cannot see what the currency said to a provider. Do not mark condition 1 from any local file.\n' "$STAMP" >> "$LOG"
fi
if [ "$VENDOR_CHANGED" = "yes" ]; then
  printf '\n## %s — VENDOR LOG CHANGED on 198 (brain-independent delta watch)\nThe provider conversation log grew since the last beat. New lines below, verbatim from the mirror — NOT interpreted, NOT classified:\n\n```\n%s\n```\n\nSteward: read core/SUPER/VENDOR_LOG_198.md before any condition-1 judgement. A vendor answer here is the Build`s load-bearing evidence.\n' "$STAMP" "$VENDOR_DELTA" >> "$LOG"
fi

# MISSED-BEAT DETECTOR (added 2026-09-04 by Claude, Super Agent cycle).
# Failure of 2026-09-03 22:15Z -> 2026-09-04 14:15Z: ~4 beats did not run at all because this
# laptop was asleep. Nothing reported it, because the only reporter WAS the beat. A watcher must
# be able to report its own absence, at least on the next breath it takes.
BEAT_STATE="$HOME/.cache/super_agent/last_beat_epoch"
mkdir -p "$(dirname "$BEAT_STATE")" 2>/dev/null || true
NOW_EPOCH=$(date -u +%s)
if [ -f "$BEAT_STATE" ]; then
  LAST_EPOCH=$(cat "$BEAT_STATE" 2>/dev/null || echo "$NOW_EPOCH")
  GAP=$(( (NOW_EPOCH - LAST_EPOCH) / 60 ))
  # schedule is every 4h; anything over 5h means beats were skipped (sleep, shutdown, cron removed)
  if [ "$GAP" -gt 300 ]; then
    MISSED=$(( GAP / 240 ))
    if [ -f "$MISSED_BEAT_ALERT_PAUSE_FILE" ]; then
      # James-authorized scoped pause: keep detecting and preserve local evidence, but do not
      # append the missed-beat entry that becomes the Telegram payload or raise its severity.
      printf '%s gap_minutes=%s estimated_beats_skipped=%s alert=suppressed pause_file=%s\n' \
        "$STAMP" "$GAP" "$MISSED" "$MISSED_BEAT_ALERT_PAUSE_FILE" >> "$MISSED_BEAT_DETECTION_LOG"
    else
      printf '\n## %s — BEATS MISSED\n- %s minutes since the previous beat (~%s beats skipped). This machine was asleep, off, or the schedule did not fire.\n- Everything the standing orders do on a beat did NOT happen during that window: the vendor log was not mirrored, the delta watch was blind, no steward verdict was appended.\n- Treat any conclusion drawn from file mtimes inside that window as unobserved, not as quiet.\n' "$STAMP" "$GAP" "$MISSED" >> "$LOG"
      BEATS_MISSED="$MISSED"
    fi
  fi
fi
echo "$NOW_EPOCH" > "$BEAT_STATE"

# Ensure the beat is visible even if the model failed to log
grep -q "$STAMP" "$LOG" 2>/dev/null || printf '\n## %s — beat ran, agent left no entry (check heartbeat_stdout.log)\n' "$STAMP" >> "$LOG"

# EXPRESS: the Super Agent speaks each beat to James's Telegram (quiet hours respected)
BEAT=$(awk '/^## /{e=""} {e=e $0 "\n"} END{print e}' "$LOG" | head -c 900)
SEV=low; PREFIX="🫀 SUPER Agent beat"
if [ "$BRAIN_OK" = "no" ] || [ "$MIRROR_OK" = "no" ]; then SEV=high; PREFIX="⛔ SUPER Agent DEGRADED — beat"; fi
if [ -n "$BEATS_MISSED" ]; then SEV=high; PREFIX="⏰ SUPER Agent — ${BEATS_MISSED} BEAT(S) MISSED — beat"; fi
# A provider speaking outranks a degraded beat: it is the one event Build #001 turns on.
if [ "$VENDOR_CHANGED" = "yes" ]; then
  SEV=high; PREFIX="📩 VENDOR LOG CHANGED — SUPER Agent beat"
  BEAT="NEW LINES IN THE PROVIDER LOG (verbatim, uninterpreted):
$VENDOR_DELTA

--- beat ---
$BEAT"
fi
"$REPO/infra/scripts/stream_to_tg.sh" --category=alignment --severity=$SEV \
  --classification=PRIVATE --body="$PREFIX $STAMP
$BEAT" 2>/dev/null || true
