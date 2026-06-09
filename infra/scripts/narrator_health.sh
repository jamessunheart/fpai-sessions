#!/bin/bash
# narrator_health.sh — daily health check for THE NARRATOR pipeline
#
# Runs once a day (noon CR via separate LaunchAgent). Verifies:
#   1. state.tsv has an OK row newer than the most-recent session transcript
#      (if newer transcripts exist with no narration → ALERT).
#      Soft rule (tightened 2026-05-20): if last OK is >90 min old AND a
#      substantive transcript was modified >LOOKBACK ago, alert. 90 min ≈
#      3 missed cycles at the new 30-min LaunchAgent cadence.
#   2. Day's sessions file exists at core/INTELLIGENCE/narrator/sessions/YYYY-MM-DD.md
#      with non-trivial content (> 200 bytes beyond frontmatter).
#   3. LaunchAgent com.sunheart.narrator-pulse is loaded (launchctl list).
#
# On failure: log to ~/.config/fpai/narrator/health_alerts.log AND push PRIVATE
# TG alert via infra/scripts/stream_to_tg.sh.
#
# Schedule: ~/Library/LaunchAgents/com.sunheart.narrator-health.plist
# (12:00 CR daily, RunAtLoad=false).
#
# Reversibility:
#   chmod -x → off
#   launchctl unload ~/Library/LaunchAgents/com.sunheart.narrator-health.plist
#
# Cost: $0 (no LLM calls).

set -uo pipefail

COCKPIT_ROOT="${HOME}/FPAI_Cockpit"
STATE_DIR="${HOME}/.config/fpai/narrator"
STATE_FILE="${STATE_DIR}/state.tsv"
HEALTH_LOG="${STATE_DIR}/health_alerts.log"
DAY_OBS_DIR="${COCKPIT_ROOT}/core/INTELLIGENCE/narrator/sessions"
STREAM_SCRIPT="${COCKPIT_ROOT}/infra/scripts/stream_to_tg.sh"
PROJECT_TRANSCRIPTS="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit"
LAUNCH_LABEL="com.sunheart.narrator-pulse"

TODAY="$(date +%Y-%m-%d)"
NOW_EPOCH="$(date +%s)"
TS_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

mkdir -p "$STATE_DIR"
touch "$HEALTH_LOG"

ALERTS=()

note() { printf '[%s] %s\n' "$TS_UTC" "$*" >> "$HEALTH_LOG"; }
alert() {
  local msg="$1"
  ALERTS+=("$msg")
  note "ALERT: $msg"
}

# ===== Check 1 — last OK run vs newest transcript =========================
last_ok_iso=""
if [ -f "$STATE_FILE" ]; then
  last_ok_iso=$(grep -F "	OK	" "$STATE_FILE" 2>/dev/null | tail -n 1 | cut -f1 || true)
fi

newest_transcript=""
newest_mod=0
if [ -d "$PROJECT_TRANSCRIPTS" ]; then
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    m=$(stat -f %m "$f" 2>/dev/null || echo 0)
    if [ "$m" -gt "$newest_mod" ]; then
      newest_mod="$m"
      newest_transcript="$f"
    fi
  done < <(find "$PROJECT_TRANSCRIPTS" -maxdepth 1 -name "*.jsonl" -mtime -1 2>/dev/null)
fi

if [ -z "$last_ok_iso" ]; then
  if [ -n "$newest_transcript" ]; then
    alert "no OK row in state.tsv at all (newest transcript: $(basename "$newest_transcript"))"
  else
    note "no OK rows yet, but also no recent transcripts — quiet day; not alerting"
  fi
else
  last_ok_epoch=$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$last_ok_iso" +%s 2>/dev/null || echo 0)
  age_minutes=$(( (NOW_EPOCH - last_ok_epoch) / 60 ))
  age_hours=$(( age_minutes / 60 ))
  if [ "$newest_mod" -gt "$last_ok_epoch" ]; then
    transcript_age_minutes=$(( (NOW_EPOCH - newest_mod) / 60 ))
    # Tightened 2026-05-20: alert if last OK is >90 min old (3 missed 30-min
    # cycles) AND newer transcript activity exists (>30 min mod age means
    # there's real session content waiting to be observed).
    if [ "$age_minutes" -ge 90 ] && [ "$transcript_age_minutes" -ge 30 ]; then
      alert "last OK ${age_minutes}m ago but transcript $(basename "$newest_transcript") modified ${transcript_age_minutes}m ago — narrator falling behind"
    else
      note "last OK ${age_minutes}m ago, newer transcript ${transcript_age_minutes}m ago — within tolerance"
    fi
  else
    note "last OK ${age_minutes}m ago, no newer transcripts since — healthy"
  fi
fi

# ===== Check 2 — today's day file has content ============================
DAY_FILE="${DAY_OBS_DIR}/${TODAY}.md"
if [ ! -f "$DAY_FILE" ]; then
  # Only alert if there's been a session transcript today
  if [ -n "$newest_transcript" ]; then
    today_transcript_count=$(find "$PROJECT_TRANSCRIPTS" -maxdepth 1 -name "*.jsonl" -newer "${STATE_DIR}/.midnight_marker" 2>/dev/null | wc -l | tr -d ' ' || echo 0)
    if [ "$today_transcript_count" -gt 0 ]; then
      alert "no day file ${DAY_FILE} but ${today_transcript_count} transcript(s) modified today"
    fi
  fi
else
  bytes=$(wc -c < "$DAY_FILE" 2>/dev/null | tr -d ' ' || echo 0)
  if [ "$bytes" -lt 200 ]; then
    alert "day file exists but only ${bytes} bytes (likely just frontmatter, no observations written)"
  else
    note "day file ${TODAY}.md has ${bytes} bytes — healthy"
  fi
fi

# Refresh midnight marker for next-day diff use
touch -t "$(date +%Y%m%d)0000" "${STATE_DIR}/.midnight_marker" 2>/dev/null || true

# ===== Check 3 — LaunchAgent loaded ======================================
if ! launchctl list 2>/dev/null | grep -q "$LAUNCH_LABEL"; then
  alert "LaunchAgent $LAUNCH_LABEL not loaded (launchctl list missing it)"
else
  note "LaunchAgent $LAUNCH_LABEL loaded — healthy"
fi

# ===== Push alerts via TG (if any) =======================================
if [ "${#ALERTS[@]}" -gt 0 ]; then
  body="Narrator health check found ${#ALERTS[@]} issue(s):"
  for a in "${ALERTS[@]}"; do
    body="${body}
• ${a}"
  done

  if [ -x "$STREAM_SCRIPT" ]; then
    "$STREAM_SCRIPT" \
      --category=narrator \
      --severity=high \
      --classification=PRIVATE \
      --body="$body" \
      --link="core/INTELLIGENCE/narrator/sessions/${TODAY}.md" \
      >/dev/null 2>&1 \
      || note "WARN: TG stream returned non-zero"
  else
    note "WOULD_PUSH_TG: $body (stream script not executable)"
  fi

  printf '%s narrator_health: %d alert(s)\n' "$TS_UTC" "${#ALERTS[@]}" >&2
  exit 1
fi

note "narrator health: all clear"
exit 0
