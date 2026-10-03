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
MISSED_RECORD=""

if [ "${1:-}" = "--missed-beat-alert-status" ]; then
  if [ -f "$MISSED_BEAT_ALERT_PAUSE_FILE" ]; then
    printf 'missed_beat_alerts=paused\npause_file=%s\n' "$MISSED_BEAT_ALERT_PAUSE_FILE"
  else
    printf 'missed_beat_alerts=active\npause_file=%s\n' "$MISSED_BEAT_ALERT_PAUSE_FILE"
  fi
  exit 0
fi

STAMP=$(date -u +"%Y-%m-%dT%H:%MZ")

# PORTABLE TIMEOUT + EARLY PATH (added 2026-10-02 by Claude, Super Agent cycle 13:05 CR).
# WHY THIS EXISTS — the sharpest finding in this file's history. For 29 days and 77 consecutive
# attempts, the 198 evidence mirror below logged "198 unreachable or log empty", and three
# documents reasoned about ssh keys, authorized_keys, Keychains and LaunchAgents on that basis.
# At 2026-10-02T18:15Z the control probe finally ran and returned, verbatim, for BOTH hosts:
#     line 101: timeout: command not found   (rc=127)
# macOS ships no `timeout` (it is GNU coreutils), and the ONLY PATH export in this script sat at
# line ~115 — 76 lines AFTER the mirror pull needed it. So `timeout 30 ssh ...` exited 127 before
# ssh was ever executed. The sensor was not failing to REACH 198; it was failing to find the
# command that would have reached it, and then naming a host as unreachable that it had never
# contacted. Nothing was wrong with 198, the key, cron or the Keychain, as far as this evidence
# goes — the wrapper did not exist. Fifth instance of one shape, and the first where the
# measuring instrument was made of the same broken part as the thing it measured.
# THE RULE THIS ENCODES: a probe that fails BEFORE it probes must not be allowed to report a
# verdict about the thing it never reached. rc=127 is not a measurement.
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
TIMEOUT_BIN=""
if command -v timeout >/dev/null 2>&1; then TIMEOUT_BIN=$(command -v timeout)
elif command -v gtimeout >/dev/null 2>&1; then TIMEOUT_BIN=$(command -v gtimeout)
fi
# ssh_to <seconds> <ssh args...> — bounded ssh that does NOT depend on a `timeout` binary.
# With no wrapper available, ssh bounds itself: ConnectTimeout caps the handshake and
# ServerAlive* caps a hung session. Never again a hard dependency on a command that may not exist.
ssh_to() {
  _to_secs="$1"; shift
  if [ -n "$TIMEOUT_BIN" ]; then
    "$TIMEOUT_BIN" "$_to_secs" ssh -o ServerAliveInterval=5 -o ServerAliveCountMax=3 "$@"
  else
    ssh -o ServerAliveInterval=5 -o ServerAliveCountMax=3 "$@"
  fi
}

cd "$REPO" || exit 1

# EVIDENCE SYNC (added 2026-09-03 by Claude, Super Agent cycle): the vendor bot's live log
# lives at /opt/VENDOR_LOG.md on 198. Nothing pulled it back, so the repo's evidence file
# silently fell behind what the currency actually promised a real person. Read-only mirror.
VLOG="$REPO/core/SUPER/VENDOR_LOG_198.md"
PREV="$HOME/.cache/super_agent/vendor_log_198.prev"
FAILSTREAK="$HOME/.cache/super_agent/mirror_fail_streak"
MIRROR_VERDICT=""
mkdir -p "$(dirname "$PREV")" 2>/dev/null || true
VTMP=$(mktemp)
DTMP=$(mktemp)
MIRROR_OK=yes
VENDOR_CHANGED=no
VENDOR_DELTA=""
if ssh_to 30 -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
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
  echo 0 > "$FAILSTREAK" 2>/dev/null || true
else
  MIRROR_OK=no
  # FAILURE HONESTY (added 2026-10-02 by Claude, Super Agent cycle). The old line said
  # "last good copy kept" on every failure. There had never been a good copy: this pull has
  # failed on every attempt since it was installed 2026-09-03T18:15Z. A message that implies
  # a success that never happened is how 75 identical failures read as weather instead of a wall.
  # COUNTER HONESTY (added 2026-10-02 by Claude, same cycle, one notch smaller than the bug above).
  # $FAILSTREAK is a cache file. It was created the moment this counter was installed, so on its
  # first failure it reported "1 consecutive attempts" for a pull that had by then failed 76 times
  # on the record. A counter that reports its own age as the world's age is the same error as a
  # stale file mistaken for the world. So the number is now DERIVED from the append-only mirror log
  # (which cannot be silently reset by clearing ~/.cache) and the cache is only a floor.
  PREV_FAILS=$(cat "$FAILSTREAK" 2>/dev/null || echo 0)
  case "$PREV_FAILS" in (*[!0-9]*|"") PREV_FAILS=0 ;; esac
  ON_RECORD=$(grep -c 'mirror pull' "$VLOG" 2>/dev/null || echo 0)
  case "$ON_RECORD" in (*[!0-9]*|"") ON_RECORD=0 ;; esac
  FAILS=$(( PREV_FAILS + 1 ))
  [ "$ON_RECORD" -ge "$FAILS" ] && FAILS=$(( ON_RECORD + 1 ))
  echo "$FAILS" > "$FAILSTREAK" 2>/dev/null || true
  if [ ! -f "$PREV" ]; then
    MIRROR_VERDICT="NEVER SUCCEEDED: $FAILS failed pulls on record, 0 successes ever, since installed 2026-09-03T18:15Z. There is no last good copy. The brain-independent delta watch is UNARMED: it needs one successful pull as its baseline, so the alarm for a provider reply cannot fire either. Treat as STRUCTURAL, not transient. CAUSE — corrected 2026-10-02 13:05 CR: for the first 77 attempts the cause was NOT ssh at all; the pull was wrapped in \`timeout\`, which macOS does not ship, so it exited 127 before ssh ran (see PORTABLE TIMEOUT at the top of this script). That wrapper is gone. If this line appears for a beat AFTER 2026-10-02T19:00Z, ssh genuinely ran and failed, and the control probe below is now a real measurement."
    printf '\n<!-- %s: mirror pull FAILED. Record: %s failed pulls, 0 successes, ever. No last good copy exists; the delta watch is unarmed. Structural, not transient. -->\n' "$STAMP" "$FAILS" >> "$VLOG" 2>/dev/null || true
  else
    MIRROR_VERDICT="failed $FAILS beat(s) in a row; a previously pulled copy is still on disk and is now stale by that much."
    printf '\n<!-- %s: mirror pull failed (%s in a row); last good copy kept but is stale -->\n' "$STAMP" "$FAILS" >> "$VLOG" 2>/dev/null || true
  fi
fi
rm -f "$VTMP" "$DTMP"

# CONTROL PROBE (added 2026-10-02 by Claude, Super Agent cycle). 76 consecutive failures of the
# 198 pull were being read as "ssh from cron is broken" — a hypothesis in the same family as B-08
# (locked Keychain). That hypothesis is weakened by a measurement nobody had made: this same Mac
# ran `git fetch server162` — which IS `ssh root@162.0.208.88` with a key, non-interactively —
# successfully on 2026-09-27, 09-28, 09-30 and 10-01, inside the same 29 days. So root ssh from
# this machine works for one host and not the other.
# A failing probe with no passing control is not a measurement. This runs the control in the SAME
# context (cron, BatchMode, same user) so the next failure is DIAGNOSTIC instead of just loud:
#   control ok + 198 fail  => 198-specific: no key in root@198:authorized_keys, or 198 refuses root ssh.
#   control fail + 198 fail => environment: cron/Keychain/agent — then B-08's family is the cause.
# It also asks the second host whether it is holding the vendor log at all, because 76 failures
# pointed at one house is also consistent with the file living in the other one.
if [ "$MIRROR_OK" = "no" ]; then
  CTRL_OUT=$(ssh_to 20 -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no \
      root@162.0.208.88 'hostname; ls -l /opt/VENDOR_LOG.md 2>&1 || echo "no /opt/VENDOR_LOG.md here"' 2>&1)
  CTRL_RC=$?
  H198_OUT=$(ssh_to 20 -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no \
      root@198.54.123.234 'hostname' 2>&1)
  H198_RC=$?
  if [ "$CTRL_RC" -eq 127 ] || [ "$H198_RC" -eq 127 ]; then
    # NOT A MEASUREMENT (added 2026-10-02 13:05 CR). rc=127 means the command never ran.
    # The 18:15Z beat hit exactly this and still printed a confident verdict blaming cron and
    # prescribing a LaunchAgent. A probe that cannot start may not name a cause.
    CTRL_VERDICT="NOT A MEASUREMENT (rc=127): the probe itself could not start — a command in it was not found, so neither host was ever contacted and NO conclusion about ssh, keys, cron or the Keychain follows from this beat. Fix the probe, then measure. (This is what happened at 2026-10-02T18:15Z: \`timeout\` does not exist on macOS and PATH was exported after this point; it has since been made portable.)"
  elif [ "$CTRL_RC" -eq 0 ]; then
    CTRL_VERDICT="CONTROL PASSED: root ssh from this cron context WORKS (to 162.0.208.88). So the 198 failure is 198-SPECIFIC (missing key in root@198 authorized_keys, or 198 refusing root ssh) and NOT a cron/Keychain problem. B-09 cause (b) is ruled out by measurement."
  else
    CTRL_VERDICT="CONTROL FAILED TOO (rc=$CTRL_RC): root ssh from this cron context does not work to EITHER host, so the cause is environmental (cron cannot use the key / no agent / Keychain locked) — same family as B-08, and the fix is a LaunchAgent in the user session, not a key on 198."
  fi
  printf '\n## %s — MIRROR CONTROL PROBE\n- %s\n- Control host root@162.0.208.88 (rc=%s), verbatim:\n```\n%s\n```\n- Target host root@198.54.123.234 (rc=%s), verbatim:\n```\n%s\n```\n- If the control lists /opt/VENDOR_LOG.md on 162, the mirror has been pointed at the wrong house for 29 days and the fix is one line in this script.\n' \
    "$STAMP" "$CTRL_VERDICT" "$CTRL_RC" "$CTRL_OUT" "$H198_RC" "$H198_OUT" >> "$LOG" 2>/dev/null || true
fi

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
  printf '\n## %s — EVIDENCE MIRROR DOWN: could not read /opt/VENDOR_LOG.md on 198. The repo cannot see what the currency said to a provider. Do not mark condition 1 from any local file.\n- Verdict: %s\n' "$STAMP" "$MIRROR_VERDICT" >> "$LOG"
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
      # James-authorized scoped pause: the ALERT is paused, the RECORD is not.
      # 2026-10-03: ~15h / 3 beats went missing and the ONLY trace was a line in ~/.cache, which
      # no agent and no human reads -- so HEARTBEAT_LOG.md, the repo's only memory of the gap,
      # said nothing and the next reader would have taken that window for a quiet one. The pause
      # doc scopes this switch to the Telegram escalation; it had also been silencing the record.
      # So: keep the local detection line, and HOLD the same BEATS MISSED section to append to
      # $LOG *after* the Telegram payload has been read, so nothing that is SENT changes.
      # Rule: a pause on an alarm must not be a pause on the record.
      printf '%s gap_minutes=%s estimated_beats_skipped=%s alert=suppressed pause_file=%s\n' \
        "$STAMP" "$GAP" "$MISSED" "$MISSED_BEAT_ALERT_PAUSE_FILE" >> "$MISSED_BEAT_DETECTION_LOG"
      MISSED_RECORD=$(printf '\n## %s - BEATS MISSED (alert suppressed by scoped pause; record kept)\n- %s minutes since the previous beat (~%s beats skipped). This machine was asleep, off, or the schedule did not fire.\n- Everything the standing orders do on a beat did NOT happen during that window: the vendor log was not mirrored, the delta watch was blind, no steward verdict was appended.\n- Treat any conclusion drawn from file mtimes inside that window as unobserved, not as quiet.\n- Telegram escalation withheld per %s. This section is evidence, not an alert.\n' "$STAMP" "$GAP" "$MISSED" "$MISSED_BEAT_ALERT_PAUSE_FILE")
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

# The record of a suppressed gap lands only now, after the payload above was read: the scoped
# pause governs what is SENT, never what is remembered.
if [ -n "$MISSED_RECORD" ]; then printf '%s\n' "$MISSED_RECORD" >> "$LOG"; fi
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
