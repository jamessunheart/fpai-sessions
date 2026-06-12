#!/bin/bash
# narrator_run.sh — activate THE NARRATOR for recent substantive sessions
#
# Cadence-through-truth · Layer 2 activation pattern (per feedback_cadence_through_truth.md).
#
# FIXED 2026-05-20 — repaired 4 bash bugs (process-substitution under set -u +
# bash 3.2 · unbound CANDIDATES · unmatched single-quote inside unquoted
# heredoc · cascading EOF). Output path moved to the canonical
# core/INTELLIGENCE/narrator/sessions/{YYYY-MM-DD}.md (append-only per spec).
#
# WHAT IT DOES:
#   1. Scans transcripts in ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/*.jsonl
#      modified within last LOOKBACK_HOURS (default 6).
#   2. For each substantive transcript (>= MIN_TURNS assistant turns), checks
#      whether it has already been narrated within MIN_INTERVAL_HOURS by
#      consulting state.tsv (not by file existence — the day's file is shared).
#   3. If due, invokes `claude -p` headless with the the-narrator agent
#      definition. Appends prose observation to:
#        core/INTELLIGENCE/narrator/sessions/{YYYY-MM-DD}.md
#      (frontmatter created on first write of the day; subsequent runs append
#      a "## HH:MM CR · <transcript-short-id>" section.)
#   4. Logs run state to ~/.config/fpai/narrator/state.tsv (audit row per run).
#   5. Runs an operational post-check — verifies state.tsv grew + day-file grew.
#      Logs loudly to stderr on any silent failure (no more silent failures).
#   6. If observation includes significance markers, pushes a PRIVATE TG alert
#      via infra/scripts/stream_to_tg.sh (markers: coherence · incoherence ·
#      regression · meta-pattern · blind spot · what-they-both-miss).
#
# INVOCATION:
#   - LaunchAgent: every 30 min (com.sunheart.narrator-pulse.plist · was 2h until 2026-05-20)
#   - On-demand: `narrator_run.sh` from terminal
#   - On-demand with specific transcript: `narrator_run.sh <transcript_path>`
#
# SMART-SKIP (added 2026-05-20 with cadence tightening to 30 min):
#   Before invoking claude (the cost-bearing step), check per-candidate:
#     - transcript mtime <= last successful run timestamp for this transcript_id
#     - AND current turn count <= last_turns + MIN_NEW_TURNS (default 3)
#   If BOTH hold → SKIP_NO_NEW_TURNS · log row to state.tsv · no claude call.
#   This keeps cost ~$2-4/day at 48 runs/day (most runs skip).
#
# Reversibility:
#   - chmod -x → loop dies
#   - launchctl unload ~/Library/LaunchAgents/com.sunheart.narrator-pulse.plist → fully off
#   - rm -rf ~/.config/fpai/narrator → reset state
#
# Cost: ~$0.05-$0.20 per narrator invocation (Opus 4.7 · ~10k input + ~2k output).
#       Bounded by MIN_INTERVAL_HOURS (default 4).

set -uo pipefail

# ===== Paths =============================================================
PROJECT_TRANSCRIPTS="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit"
COCKPIT_ROOT="${HOME}/FPAI_Cockpit"
DAY_OBS_DIR="${COCKPIT_ROOT}/core/INTELLIGENCE/narrator/sessions"
STATE_DIR="${HOME}/.config/fpai/narrator"
STATE_FILE="${STATE_DIR}/state.tsv"
RUN_LOG="${STATE_DIR}/run.log"
STREAM_SCRIPT="${COCKPIT_ROOT}/infra/scripts/stream_to_tg.sh"
CLAUDE_BIN="${HOME}/.local/bin/claude"
NARRATOR_AGENT="${COCKPIT_ROOT}/.claude/agents/the-narrator.md"

LOOKBACK_HOURS="${LOOKBACK_HOURS:-6}"
MIN_TURNS="${MIN_TURNS:-5}"
MIN_INTERVAL_HOURS="${MIN_INTERVAL_HOURS:-4}"
MIN_NEW_TURNS="${MIN_NEW_TURNS:-3}"  # smart-skip threshold (added 2026-05-20)
TRIGGER="${NARRATOR_TRIGGER:-launchagent}"  # one of: launchagent · inline-ember · hook · manual
TODAY="$(date +%Y-%m-%d)"
TS_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
CR_TIME="$(TZ=America/Costa_Rica date +%H:%M)"

mkdir -p "$STATE_DIR" "$DAY_OBS_DIR"

# State file header (created once)
if [ ! -s "$STATE_FILE" ]; then
  printf '# Narrator run state · TSV: timestamp_utc\ttranscript_id\tturn_count\tobs_file\texit_status\tcost_est_usd\n' > "$STATE_FILE"
fi

DAY_FILE="${DAY_OBS_DIR}/${TODAY}.md"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*" | tee -a "$RUN_LOG" >&2; }
err() { printf '[%s] ERROR: %s\n' "$(date -u +%H:%M:%SZ)" "$*" | tee -a "$RUN_LOG" >&2; }

# Snapshot pre-state for operational post-check
PRE_STATE_LINES=$(wc -l < "$STATE_FILE" 2>/dev/null | tr -d ' ' || echo 0)
PRE_DAY_BYTES=0
if [ -f "$DAY_FILE" ]; then
  PRE_DAY_BYTES=$(wc -c < "$DAY_FILE" 2>/dev/null | tr -d ' ' || echo 0)
fi

# ===== Sanity checks =====================================================
if [ ! -x "$CLAUDE_BIN" ]; then
  err "claude CLI not found or not executable at $CLAUDE_BIN"
  exit 1
fi
if [ ! -d "$PROJECT_TRANSCRIPTS" ]; then
  err "project transcripts dir missing: $PROJECT_TRANSCRIPTS"
  exit 1
fi
if [ ! -f "$NARRATOR_AGENT" ]; then
  err "narrator agent file missing: $NARRATOR_AGENT"
  exit 1
fi

# ===== Collect candidate transcripts =====================================
# Avoid `mapfile < <(...)` because process-substitution inside this script
# under bash 3.2 + set -u was the source of the original bugs. Use a tempfile.
CANDIDATES=()

if [ -n "${1:-}" ]; then
  # explicit transcript argument
  CANDIDATES=("$1")
else
  CAND_LIST=$(mktemp -t narrator-cands-XXXXXX)
  find "$PROJECT_TRANSCRIPTS" -maxdepth 1 -name "*.jsonl" -mtime -1 2>/dev/null \
    | while IFS= read -r f; do
        mod_epoch=$(stat -f %m "$f" 2>/dev/null || echo 0)
        now_epoch=$(date +%s)
        diff_hours=$(( (now_epoch - mod_epoch) / 3600 ))
        if [ "$diff_hours" -le "$LOOKBACK_HOURS" ]; then
          printf '%s\n' "$f"
        fi
      done > "$CAND_LIST"

  if [ -s "$CAND_LIST" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] && CANDIDATES+=("$line")
    done < "$CAND_LIST"
  fi
  rm -f "$CAND_LIST"
fi

if [ "${#CANDIDATES[@]}" -eq 0 ]; then
  log "no transcripts modified in last ${LOOKBACK_HOURS}h — exiting clean"
  exit 0
fi

log "found ${#CANDIDATES[@]} candidate transcript(s) within ${LOOKBACK_HOURS}h"

# ===== Initialize day file if first run of the day =======================
ensure_day_file_frontmatter() {
  if [ ! -f "$DAY_FILE" ]; then
    cat > "$DAY_FILE" <<DAY_HEAD
---
date: ${TODAY}
classification: COUNCIL-OPEN
narrator: the-narrator
arc: accumulating narrator observations for ${TODAY}
---

DAY_HEAD
  fi
}

# ===== Per-transcript processing =========================================
NEW_OBS_WRITTEN=0
TOTAL_COST=0

for transcript in "${CANDIDATES[@]}"; do
  [ -f "$transcript" ] || continue
  transcript_id="$(basename "$transcript" .jsonl)"
  short_id="${transcript_id:0:8}"

  # Count assistant turns
  turn_count=$(tail -n 5000 "$transcript" 2>/dev/null \
    | jq -s -r 'map(select(.type=="assistant")) | length' 2>/dev/null || echo 0)
  [ -z "$turn_count" ] && turn_count=0
  [ "$turn_count" = "null" ] && turn_count=0

  if [ "$turn_count" -lt "$MIN_TURNS" ]; then
    log "  ${short_id}: only ${turn_count} turn(s) — skip (min ${MIN_TURNS})"
    continue
  fi

  # Look up last successful run for this transcript_id from state.tsv. Capture
  # both the timestamp AND the turn_count at that point — both needed for
  # smart-skip (mtime+turn_count gate) and for the MIN_INTERVAL_HOURS floor.
  last_run_epoch=0
  last_run_turns=0
  if [ -f "$STATE_FILE" ]; then
    last_ok_row=$(grep -F "	${transcript_id}	" "$STATE_FILE" 2>/dev/null \
      | grep -F "	OK	" \
      | tail -n 1 || true)
    if [ -n "${last_ok_row:-}" ]; then
      last_run_iso=$(printf '%s\n' "$last_ok_row" | cut -f1)
      last_run_turns=$(printf '%s\n' "$last_ok_row" | cut -f3)
      [ -z "$last_run_turns" ] && last_run_turns=0
      # macOS date parsing of ISO-8601 UTC
      last_run_epoch=$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$last_run_iso" +%s 2>/dev/null || echo 0)
    fi
  fi
  now_epoch=$(date +%s)

  # ===== Smart-skip (added 2026-05-20 with cadence tightened to 30 min) ===
  # Per project_narrator_surfaces.md "Real-time trigger discipline" section:
  # the LaunchAgent at 30 min cadence is the safety net · skip when there are
  # no new substantive turns to observe.
  if [ "$last_run_epoch" -gt 0 ]; then
    transcript_mtime=$(stat -f %m "$transcript" 2>/dev/null || echo 0)
    new_turns=$(( turn_count - last_run_turns ))
    # Per dispatch spec: skip when mtime <= last_run_ts AND current_turns <=
    # last_turns + MIN_NEW_TURNS. I.e., proceed only when transcript has been
    # touched since last run AND has at least MIN_NEW_TURNS+1 new turns.
    if [ "$transcript_mtime" -le "$last_run_epoch" ] && [ "$new_turns" -le "$MIN_NEW_TURNS" ]; then
      log "  ${short_id}: mtime <= last_run AND new_turns=${new_turns} <= ${MIN_NEW_TURNS} — SKIP_NO_NEW_TURNS"
      printf '%s\t%s\t%s\t%s\tSKIP_NO_NEW_TURNS\t0\n' \
        "$TS_UTC" "$transcript_id" "$turn_count" "$DAY_FILE" >> "$STATE_FILE"
      continue
    fi
  fi

  # MIN_INTERVAL_HOURS floor (kept as hard lower bound · superseded operationally
  # by smart-skip above · still useful for very chatty transcripts).
  age_h=$(( (now_epoch - last_run_epoch) / 3600 ))
  if [ "$last_run_epoch" -gt 0 ] && [ "$age_h" -lt "$MIN_INTERVAL_HOURS" ]; then
    log "  ${short_id}: narrated ${age_h}h ago — skip (min interval ${MIN_INTERVAL_HOURS}h)"
    continue
  fi

  log "  ${short_id}: ${turn_count} turns · narrating → ${TODAY}.md"

  ensure_day_file_frontmatter

  # ===== Extract last ~50 turns as readable excerpt =====================
  excerpt_file=$(mktemp -t narrator-excerpt-XXXXXX)
  tail -n 2000 "$transcript" 2>/dev/null \
    | jq -s -r --arg max 50 '
        map(select(.type=="assistant" or .type=="user"))
        | .[-($max|tonumber):]
        | map(
            if .type=="assistant" then
              "[assistant @ \(.timestamp // "?")] " + (
                (.message.content // [] | map(select(.type=="text") | .text) | join("\n"))
                // "(no text)"
              )
            else
              "[user @ \(.timestamp // "?")] " + (
                (.message.content // "" | if type=="string" then . else (map(select(.type=="text") | .text) | join("\n")) end)
                // "(no text)"
              )
            end)
        | join("\n\n---\n\n")
      ' > "$excerpt_file" 2>/dev/null \
    || printf '(transcript extraction failed)\n' > "$excerpt_file"

  excerpt_size=$(wc -c < "$excerpt_file" 2>/dev/null | tr -d ' ' || echo 0)
  log "    excerpt: ${excerpt_size} bytes"

  # ===== Build prompt via quoted-heredoc + placeholder substitution =====
  # Quoted <<'PROMPT_EOF' keeps jq filters / quotes literal (this is what
  # broke the old version). We then substitute the few real variables we need
  # via printf afterward.
  prompt_template=$(mktemp -t narrator-prompt-XXXXXX)
  cat > "$prompt_template" <<'PROMPT_EOF'
You are running THE NARRATOR via headless invocation. Read your spec at __AGENT_PATH__ and the mandatory pre-read sequence in it FIRST.

Then observe the session transcript excerpt below (last ~50 turns of session __TRANSCRIPT_ID__, __TURN_COUNT__ total assistant turns).

Write a content-grade prose observation — 200-400 words, third-person, cinematic, observing BOTH parties (James AND Ember). Quote moments when they carry signal. Name what wasn't named. Do NOT recap the FLOW stream.

APPEND your observation to EXACTLY this file (do not overwrite):
  __DAY_FILE__

Append format (Markdown, exactly this shape):

## __CR_TIME__ CR · __SHORT_ID__ · trigger: __TRIGGER__ · "<descriptive title you choose>"

<200-400 words of prose · third-person · observing both parties · specific quotes when relevant>

<then a blank line · then end>

If the file does not yet contain frontmatter (---...---), do nothing about it — the runner has already written the frontmatter. Just append your ## section to the end of the file.

After writing, output a single line on stdout: NARRATOR_DONE: __DAY_FILE__

--- SESSION EXCERPT BELOW ---

__EXCERPT_PLACEHOLDER__

--- END EXCERPT ---
PROMPT_EOF

  # Export placeholders for the python substitution below
  export NARRATOR_AGENT TRANSCRIPT_ID="$transcript_id" TURN_COUNT="$turn_count" \
         DAY_FILE CR_TIME SHORT_ID="$short_id" TRIGGER

  prompt_file=$(mktemp -t narrator-prompt-final-XXXXXX)
  # Use python for safe substitution — sed gets brittle with markdown content.
  python3 - "$prompt_template" "$prompt_file" "$excerpt_file" <<'PY'
import sys, os
tmpl_path, out_path, excerpt_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(tmpl_path) as f:
    t = f.read()
with open(excerpt_path) as f:
    excerpt = f.read()
subs = {
    "__AGENT_PATH__":         os.environ.get("NARRATOR_AGENT", ""),
    "__TRANSCRIPT_ID__":      os.environ.get("TRANSCRIPT_ID", ""),
    "__TURN_COUNT__":         os.environ.get("TURN_COUNT", ""),
    "__DAY_FILE__":           os.environ.get("DAY_FILE", ""),
    "__CR_TIME__":            os.environ.get("CR_TIME", ""),
    "__SHORT_ID__":           os.environ.get("SHORT_ID", ""),
    "__TRIGGER__":            os.environ.get("TRIGGER", "launchagent"),
}
for k, v in subs.items():
    t = t.replace(k, v)
t = t.replace("__EXCERPT_PLACEHOLDER__", excerpt)
with open(out_path, "w") as f:
    f.write(t)
PY

  # Snapshot day-file size before claude invocation, so we can detect a real append
  pre_invoke_bytes=0
  [ -f "$DAY_FILE" ] && pre_invoke_bytes=$(wc -c < "$DAY_FILE" 2>/dev/null | tr -d ' ' || echo 0)

  # Portable timeout wrapper — macOS doesn't ship coreutils `timeout`.
  # Use `gtimeout` if present (brew coreutils), `timeout` if present, else
  # perl-based fallback that kills the process after N seconds.
  TIMEOUT_SEC=300
  if command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD=(gtimeout "$TIMEOUT_SEC")
  elif command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD=(timeout "$TIMEOUT_SEC")
  else
    TIMEOUT_CMD=(perl -e '
      use strict; use warnings;
      my $secs = shift;
      my $pid = fork();
      die "fork failed: $!" unless defined $pid;
      if ($pid == 0) { exec(@ARGV) or die "exec failed: $!"; }
      local $SIG{ALRM} = sub { kill 9, $pid; exit 124; };
      alarm $secs;
      waitpid($pid, 0);
      exit($? >> 8);
    ' "$TIMEOUT_SEC")
  fi

  start_epoch=$(date +%s)
  set +e
  output=$(cat "$prompt_file" | "${TIMEOUT_CMD[@]}" "$CLAUDE_BIN" \
    --model claude-opus-4-7 \
    --print \
    --output-format text \
    --permission-mode bypassPermissions \
    2>&1)
  exit_code=$?
  set -e
  end_epoch=$(date +%s)
  elapsed=$((end_epoch - start_epoch))

  rm -f "$excerpt_file" "$prompt_template" "$prompt_file"

  if [ "$exit_code" -ne 0 ]; then
    err "    FAILED (exit ${exit_code}, ${elapsed}s) · transcript=${short_id}"
    printf '%s\t%s\t%s\t%s\tERROR_%d\t0\n' \
      "$TS_UTC" "$transcript_id" "$turn_count" "$DAY_FILE" "$exit_code" >> "$STATE_FILE"
    continue
  fi

  # Verify a real append happened (operational check #1)
  post_invoke_bytes=0
  [ -f "$DAY_FILE" ] && post_invoke_bytes=$(wc -c < "$DAY_FILE" 2>/dev/null | tr -d ' ' || echo 0)
  delta_bytes=$(( post_invoke_bytes - pre_invoke_bytes ))

  if [ "$delta_bytes" -lt 200 ]; then
    err "    NO_APPEND · exit=0 but day-file grew only ${delta_bytes} bytes (< 200) · transcript=${short_id}"
    err "    claude stdout tail: $(printf '%s' "$output" | tail -c 400)"
    printf '%s\t%s\t%s\t%s\tNO_APPEND\t0\n' \
      "$TS_UTC" "$transcript_id" "$turn_count" "$DAY_FILE" >> "$STATE_FILE"
    continue
  fi

  # Cost estimate: rough — excerpt bytes / 4 ≈ input tokens · output ~2k tokens
  # Opus 4.7 ≈ $15/M input + $75/M output (rounded). Per call ~$0.05-$0.20.
  in_tok=$(( excerpt_size / 4 ))
  cost_est=$(python3 -c "print(f'{($in_tok * 15 + 2000 * 75) / 1000000:.3f}')" 2>/dev/null || echo "0.10")
  TOTAL_COST=$(python3 -c "print(f'{$TOTAL_COST + $cost_est:.3f}')" 2>/dev/null || echo "$cost_est")

  log "    SUCCESS (${elapsed}s · +${delta_bytes} bytes · ~\$${cost_est})"
  printf '%s\t%s\t%s\t%s\tOK\t%s\n' \
    "$TS_UTC" "$transcript_id" "$turn_count" "$DAY_FILE" "$cost_est" >> "$STATE_FILE"
  NEW_OBS_WRITTEN=$(( NEW_OBS_WRITTEN + 1 ))

  # ===== Significance-marker detection → PRIVATE TG push ================
  # Read just the newly-appended bytes
  new_text=$(tail -c "$delta_bytes" "$DAY_FILE" 2>/dev/null || true)
  markers=""
  for kw in "coherence" "incoherence" "regression" "meta-pattern" "blind spot" "blind-spot" "what they both miss" "what-they-both-miss"; do
    if printf '%s' "$new_text" | grep -qiF "$kw"; then
      markers="${markers}${kw} · "
    fi
  done

  if [ -n "$markers" ]; then
    if [ -x "$STREAM_SCRIPT" ]; then
      # First non-empty line of the appended section as summary
      summary=$(printf '%s' "$new_text" \
        | awk 'NF && !/^##/ && !/^---/ {print; exit}' \
        | head -c 220)
      [ -z "$summary" ] && summary="Narrator observation logged (${short_id})"
      "$STREAM_SCRIPT" \
        --category=narrator \
        --severity=med \
        --classification=PRIVATE \
        --body="Narrator [${short_id}] markers: ${markers%· }
${summary}" \
        --link="core/INTELLIGENCE/narrator/sessions/${TODAY}.md" \
        >/dev/null 2>&1 \
        || log "    WARN: TG stream returned non-zero (non-fatal)"
      log "    TG_PUSH · markers=${markers%· }"
    else
      err "    WOULD_PUSH_TG: markers=${markers%· } (stream script not executable: $STREAM_SCRIPT)"
    fi
  fi
done

# ===== Operational post-check ============================================
POST_STATE_LINES=$(wc -l < "$STATE_FILE" 2>/dev/null | tr -d ' ' || echo 0)
POST_DAY_BYTES=0
[ -f "$DAY_FILE" ] && POST_DAY_BYTES=$(wc -c < "$DAY_FILE" 2>/dev/null | tr -d ' ' || echo 0)

state_delta=$(( POST_STATE_LINES - PRE_STATE_LINES ))
day_delta=$(( POST_DAY_BYTES - PRE_DAY_BYTES ))

log "post-check: state.tsv rows +${state_delta} · day-file bytes +${day_delta} · new_obs=${NEW_OBS_WRITTEN} · total_cost~\$${TOTAL_COST}"

if [ "${#CANDIDATES[@]}" -gt 0 ] && [ "$NEW_OBS_WRITTEN" -eq 0 ] && [ "$state_delta" -eq 0 ]; then
  # We had candidates but wrote nothing AND added no state row — that's silent failure territory.
  err "OPERATIONAL_CHECK_FAIL: ${#CANDIDATES[@]} candidate(s) processed but zero state rows added and zero observations written. Investigate run.log."
  exit 2
fi

if [ "$NEW_OBS_WRITTEN" -gt 0 ] && [ "$day_delta" -lt 200 ]; then
  err "OPERATIONAL_CHECK_FAIL: claimed ${NEW_OBS_WRITTEN} new observation(s) but day-file only grew ${day_delta} bytes."
  exit 2
fi

log "narrator_run complete · new=${NEW_OBS_WRITTEN} · cost~\$${TOTAL_COST}"
exit 0
