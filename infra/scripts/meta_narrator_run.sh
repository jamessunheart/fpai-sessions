#!/bin/bash
# meta_narrator_run.sh — activate META-NARRATOR audit pass on recent Narrator logs
#
# Cadence-through-truth · Layer 3 (truth-redundancy) audit of Layer 2 (Narrator).
# Per feedback_cadence_through_truth.md.
#
# WHAT IT DOES:
#   1. Scans Narrator logs in memory/observations/narrator/ modified within LOOKBACK_DAYS.
#   2. For each Narrator log without a corresponding meta_narrator audit, invokes
#      `claude -p` headless with the-meta-narrator agent against the Narrator log
#      + its ground-truth source transcript.
#   3. Writes audit log to:
#        memory/observations/meta_narrator/YYYY-MM-DD_audit_<narrator-log-short-id>.md
#   4. Logs run state to ~/.config/fpai/meta_narrator/state.tsv
#
# INVOCATION:
#   - LaunchAgent: weekly Sundays 08:00 (com.sunheart.meta-narrator-weekly.plist)
#   - On-demand: `meta_narrator_run.sh` from terminal
#   - On-demand with specific narrator log: `meta_narrator_run.sh <narrator_log_path>`
#
# Reversibility:
#   - chmod -x this file → loop dies
#   - launchctl unload ~/Library/LaunchAgents/com.sunheart.meta-narrator-weekly.plist → fully off
#   - rm -rf ~/.config/fpai/meta_narrator → reset state (audit logs preserved separately)
#
# Cost: ~$0.50–$2.00 per audit (Opus reads narrator log + transcript excerpt + spec).
#       Bounded by 1-per-narrator-log policy (no re-audits unless narrator log itself updated).

set -uo pipefail

OBS_DIR="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/observations/narrator"
AUDIT_DIR="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/observations/meta_narrator"
TRANSCRIPTS_DIR="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit"
STATE_DIR="${HOME}/.config/fpai/meta_narrator"
STATE_FILE="${STATE_DIR}/state.tsv"
LOG="${STATE_DIR}/run.log"
CLAUDE_BIN="${HOME}/.local/bin/claude"

LOOKBACK_DAYS="${LOOKBACK_DAYS:-7}"
MAX_AUDITS_PER_RUN="${MAX_AUDITS_PER_RUN:-3}"
TODAY=$(date +%Y-%m-%d)
TS_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)

mkdir -p "$STATE_DIR" "$AUDIT_DIR"

log() { echo "[$(date -u +%H:%M:%SZ)] $*" | tee -a "$LOG" >&2; }

if [ ! -x "$CLAUDE_BIN" ]; then
  log "ERROR: claude CLI not found at $CLAUDE_BIN"
  exit 1
fi
if [ ! -d "$OBS_DIR" ]; then
  log "ERROR: narrator observations dir missing: $OBS_DIR"
  exit 1
fi

# ----- collect candidate narrator logs -----
if [ -n "${1:-}" ]; then
  # explicit narrator log argument
  CANDIDATES=("$1")
else
  # narrator logs modified within LOOKBACK_DAYS
  mapfile -t CANDIDATES < <(find "$OBS_DIR" -maxdepth 1 -name "*.md" -not -name ".*" \
    -mtime -"${LOOKBACK_DAYS}" 2>/dev/null | sort)
fi

if [ ${#CANDIDATES[@]} -eq 0 ]; then
  log "No narrator logs modified in last ${LOOKBACK_DAYS}d — exiting clean"
  exit 0
fi

log "Found ${#CANDIDATES[@]} candidate narrator log(s); max audits this run: ${MAX_AUDITS_PER_RUN}"

audits_done=0

# ----- per-log audit processing -----
for narrator_log in "${CANDIDATES[@]}"; do
  [ -f "$narrator_log" ] || continue
  [ "$audits_done" -ge "$MAX_AUDITS_PER_RUN" ] && { log "Hit max audits cap ($MAX_AUDITS_PER_RUN) — stopping"; break; }

  log_basename=$(basename "$narrator_log" .md)
  short_id="${log_basename: -8}"
  audit_file="${AUDIT_DIR}/${TODAY}_audit_${log_basename}.md"

  # skip if audit already exists AND is newer than the narrator log
  if [ -f "$audit_file" ]; then
    audit_mtime=$(stat -f %m "$audit_file" 2>/dev/null || echo 0)
    log_mtime=$(stat -f %m "$narrator_log" 2>/dev/null || echo 0)
    if [ "$audit_mtime" -gt "$log_mtime" ]; then
      log "  $log_basename: audit already current — skip"
      continue
    fi
  fi

  # check log size
  log_size=$(wc -c < "$narrator_log" 2>/dev/null || echo 0)
  if [ "$log_size" -lt 500 ]; then
    log "  $log_basename: only ${log_size} bytes — skip (too small to audit meaningfully)"
    continue
  fi

  log "  $log_basename: ${log_size} bytes · auditing → $(basename "$audit_file")"

  # try to identify ground-truth transcript
  # narrator log format: YYYY-MM-DD_<short-id>.md OR YYYY-MM-DD_<slug>.md
  # short-id (8 chars) matches transcript_id prefix
  source_transcript=""
  short_match="${log_basename##*_}"
  if [ ${#short_match} -ge 6 ]; then
    # try to find matching transcript by prefix
    for tx in "$TRANSCRIPTS_DIR"/*.jsonl; do
      tx_id=$(basename "$tx" .jsonl)
      if [[ "$tx_id" == "$short_match"* ]] || [[ "$short_match" == "${tx_id:0:8}" ]] || [[ "$short_match" == "${tx_id:0:6}" ]]; then
        source_transcript="$tx"
        break
      fi
    done
  fi

  if [ -z "$source_transcript" ] && [ -f "$narrator_log" ]; then
    # fallback: try to extract transcript id from the narrator log's first 200 lines
    extracted=$(head -200 "$narrator_log" | grep -oE 'session[ -]?[a-f0-9]{8}' | head -1 | grep -oE '[a-f0-9]{8}' || true)
    if [ -n "$extracted" ]; then
      for tx in "$TRANSCRIPTS_DIR"/*.jsonl; do
        tx_id=$(basename "$tx" .jsonl)
        if [[ "$tx_id" == "$extracted"* ]]; then
          source_transcript="$tx"
          break
        fi
      done
    fi
  fi

  # build transcript excerpt if available
  transcript_excerpt_path=""
  if [ -n "$source_transcript" ] && [ -f "$source_transcript" ]; then
    transcript_excerpt_path=$(mktemp -t meta-narrator-excerpt-XXXXXX)
    tail -n 3000 "$source_transcript" 2>/dev/null \
      | jq -s -r --arg max 80 '
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
        ' > "$transcript_excerpt_path" 2>/dev/null || echo "(transcript extraction failed)" > "$transcript_excerpt_path"
    log "    ground truth: $(basename "$source_transcript") ($(wc -c < "$transcript_excerpt_path") bytes excerpt)"
  else
    log "    WARN: no source transcript identified — will audit with insufficient ground truth"
  fi

  # invoke claude headless with meta-narrator agent
  ground_truth_block=""
  if [ -n "$transcript_excerpt_path" ] && [ -f "$transcript_excerpt_path" ]; then
    ground_truth_block="--- SOURCE TRANSCRIPT EXCERPT (last ~80 turns) ---

$(cat "$transcript_excerpt_path")

--- END TRANSCRIPT EXCERPT ---"
  else
    ground_truth_block="--- GROUND TRUTH UNAVAILABLE ---
No source transcript could be matched to this Narrator log. Mark verdict as INSUFFICIENT GROUND TRUTH and audit only against the narrator log's internal coherence + spec compliance."
  fi

  prompt=$(cat <<EOF
You are running THE META-NARRATOR via headless invocation. Read your spec at /Users/jamessunheart/FPAI_Cockpit/.claude/agents/meta-narrator.md FIRST and follow the mandatory pre-read sequence.

You are auditing this Narrator log:
  $narrator_log

Write your audit to EXACTLY this path:
  $audit_file

Use the canonical format from your spec. Cite specific timestamps, quotes, file paths. Be forensic, not narrative.

--- NARRATOR LOG BEING AUDITED ---

$(cat "$narrator_log")

--- END NARRATOR LOG ---

$ground_truth_block

After writing the audit, output a single line: "META_NARRATOR_DONE: <audit_file_path> · verdict=<verdict-tag>"
EOF
)

  start_epoch=$(date +%s)
  set +e
  output=$(echo "$prompt" | timeout 360 "$CLAUDE_BIN" \
    --model claude-opus-4-7 \
    --print \
    --output-format text \
    --permission-mode bypassPermissions \
    2>&1)
  exit_code=$?
  set -e
  end_epoch=$(date +%s)
  elapsed=$((end_epoch - start_epoch))

  [ -n "$transcript_excerpt_path" ] && rm -f "$transcript_excerpt_path"

  if [ $exit_code -ne 0 ]; then
    log "    FAILED (exit $exit_code, ${elapsed}s)"
    echo -e "${TS_UTC}\t${narrator_log}\t${audit_file}\t0\tERROR_${exit_code}\t0" >> "$STATE_FILE"
    continue
  fi

  if [ -f "$audit_file" ]; then
    drift_flags=$(grep -cE '^### Flag [0-9]+' "$audit_file" 2>/dev/null || echo 0)
    verdict=$(grep -oE '(HIGH FIDELITY|MINOR DRIFT|MATERIAL DRIFT|INSUFFICIENT GROUND TRUTH)' "$audit_file" | head -1 || echo "UNKNOWN")
    log "    SUCCESS (${elapsed}s, $(wc -c < "$audit_file") bytes, verdict=$verdict, flags=$drift_flags)"
    cost_est="1.50"
    echo -e "${TS_UTC}\t${narrator_log}\t${audit_file}\t${drift_flags}\tOK_${verdict// /_}\t${cost_est}" >> "$STATE_FILE"
    audits_done=$((audits_done + 1))

    # ----- brain → TG stream (Phase 1) -----
    STREAM_SCRIPT="${HOME}/FPAI_Cockpit/infra/scripts/stream_to_tg.sh"
    if [ -x "$STREAM_SCRIPT" ]; then
      # Severity escalates with verdict; MATERIAL DRIFT = high
      msev="med"
      case "$verdict" in
        "MATERIAL DRIFT") msev="high" ;;
        "MINOR DRIFT")    msev="med"  ;;
        "HIGH FIDELITY")  msev="low"  ;;
      esac
      "$STREAM_SCRIPT" \
        --category=meta-narrator \
        --severity="$msev" \
        --classification=PRIVATE \
        --body="Meta-Narrator audit: verdict=${verdict} · ${drift_flags} flag(s) · auditing $(basename "$narrator_log")" \
        --link="$(basename "$audit_file")" \
        >/dev/null 2>&1 || log "    WARN: TG stream failed (non-fatal)"
    fi
  else
    log "    WARN: claude returned 0 but audit file missing"
    echo -e "${TS_UTC}\t${narrator_log}\t${audit_file}\t0\tNO_FILE\t0" >> "$STATE_FILE"
  fi
done

log "meta_narrator_run complete · $audits_done audit(s) generated"
exit 0
