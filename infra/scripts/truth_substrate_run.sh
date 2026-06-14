#!/bin/bash
# truth_substrate_run.sh — 3-agent truth substrate activation pipeline
#
# Per [[project-truth-substrate-architecture]] · the canonical newsroom-style 3-agent model.
# Supersedes narrator_run.sh + meta_narrator_run.sh (legacy two-layer flow).
#
# PIPELINE:
#   1. TRUE Narrator (.claude/agents/true-narrator.md) reads recent substantive
#      session transcripts + Ember journal + file diffs. Writes PRIVATE-tier
#      observation logs to memory/observations/true_narrator/.
#   2. Privacy Narrator (.claude/agents/privacy-narrator.md) reads each new
#      TRUE Narrator log + Ember journal. Classifies each piece of content to
#      tier (PRIVATE / COUNCIL-RESTRICTED / COUNCIL-OPEN / PUBLIC). Writes
#      audit to ~/.config/fpai/classification_audit/. Routes sanitized content
#      to ~/.config/fpai/tier_routing/<tier>/.
#   3. The Publisher (.claude/agents/the-publisher.md · a.k.a. Reporter Agent
#      in canonical) reads ~/.config/fpai/tier_routing/public/staged_for_review/
#      and STAGES content for James first-publish greenlight (does NOT push live
#      until James approves first batch · STAGE-ONLY mode).
#
# INVOCATION:
#   - On-demand: truth_substrate_run.sh
#   - Specific transcript: truth_substrate_run.sh <transcript_path>
#   - Run only N stages: truth_substrate_run.sh --stages=true,privacy
#   - LaunchAgent (Phase 2): every 2h or at SETTLE hook
#
# Reversibility:
#   - chmod -x truth_substrate_run.sh → pipeline off
#   - delete generated content in tier_routing/* → reversible until publish
#   - LIVE publishes (Publisher Phase 2+) → amend-with-audit only
#
# Cost: ~$1.50-$3.50 per full pipeline run (Opus across 3 agents on full session).
#       Bounded by MIN_INTERVAL_HOURS (default 4) per-transcript.

set -uo pipefail

PROJECT_TRANSCRIPTS="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit"
TRUE_OBS_DIR="${PROJECT_TRANSCRIPTS}/memory/observations/true_narrator"
PRIVACY_AUDIT_DIR="${HOME}/.config/fpai/classification_audit"
TIER_ROUTING_DIR="${HOME}/.config/fpai/tier_routing"
PUBLIC_STAGING_DIR="${TIER_ROUTING_DIR}/public/staged_for_review"
PUBLISH_AUDIT_DIR="${HOME}/.config/fpai/publish_audit"
STATE_DIR="${HOME}/.config/fpai/truth_substrate"
STATE_FILE="${STATE_DIR}/state.tsv"
LOG="${STATE_DIR}/run.log"
CLAUDE_BIN="${HOME}/.local/bin/claude"

LOOKBACK_HOURS="${LOOKBACK_HOURS:-6}"
MIN_TURNS="${MIN_TURNS:-5}"
MIN_INTERVAL_HOURS="${MIN_INTERVAL_HOURS:-4}"
STAGES="${STAGES:-true,privacy,publisher}"
TODAY=$(date +%Y-%m-%d)
TS_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Parse --stages= flag if present
for arg in "$@"; do
  case "$arg" in
    --stages=*) STAGES="${arg#*=}";;
  esac
done

mkdir -p "$STATE_DIR" "$TRUE_OBS_DIR" "$PRIVACY_AUDIT_DIR" \
  "$TIER_ROUTING_DIR/private" "$TIER_ROUTING_DIR/council-restricted" \
  "$TIER_ROUTING_DIR/council-open" "$PUBLIC_STAGING_DIR" \
  "$PUBLISH_AUDIT_DIR"

log() { echo "[$(date -u +%H:%M:%SZ)] $*" | tee -a "$LOG" >&2; }

if [ ! -x "$CLAUDE_BIN" ]; then
  log "ERROR: claude CLI not found at $CLAUDE_BIN"
  exit 1
fi

run_stage() {
  local stage="$1"
  case ",${STAGES}," in
    *",${stage},"*) return 0 ;;
    *) return 1 ;;
  esac
}

# =============================================================
# STAGE 1 — TRUE Narrator
# =============================================================
if run_stage "true"; then
  log "STAGE 1 · TRUE Narrator"

  if [ -n "${1:-}" ] && [ "${1:-}" != "--stages="* ]; then
    CANDIDATES=("$1")
  else
    mapfile -t CANDIDATES < <(find "$PROJECT_TRANSCRIPTS" -maxdepth 1 -name "*.jsonl" \
      -mtime -1 2>/dev/null \
      | while read -r f; do
          mod_epoch=$(stat -f %m "$f" 2>/dev/null || echo 0)
          now_epoch=$(date +%s)
          diff_hours=$(( (now_epoch - mod_epoch) / 3600 ))
          if [ "$diff_hours" -le "$LOOKBACK_HOURS" ]; then
            echo "$f"
          fi
        done)
  fi

  for transcript in "${CANDIDATES[@]}"; do
    [ -f "$transcript" ] || continue
    transcript_id=$(basename "$transcript" .jsonl)
    short_id="${transcript_id:0:8}"

    turn_count=$(tail -n 5000 "$transcript" 2>/dev/null \
      | jq -s -r 'map(select(.type=="assistant")) | length' 2>/dev/null || echo 0)
    [ -z "$turn_count" ] && turn_count=0
    [ "$turn_count" = "null" ] && turn_count=0

    if [ "$turn_count" -lt "$MIN_TURNS" ]; then
      log "  $short_id: $turn_count turns — skip (min $MIN_TURNS)"
      continue
    fi

    obs_file="${TRUE_OBS_DIR}/${TODAY}_${short_id}.md"
    if [ -f "$obs_file" ]; then
      file_age_h=$(( ( $(date +%s) - $(stat -f %m "$obs_file" 2>/dev/null || echo 0) ) / 3600 ))
      if [ "$file_age_h" -lt "$MIN_INTERVAL_HOURS" ]; then
        log "  $short_id: TRUE narrated ${file_age_h}h ago — skip"
        continue
      fi
    fi

    log "  $short_id: $turn_count turns · TRUE narrating → $(basename "$obs_file")"

    excerpt_file=$(mktemp -t true-narrator-excerpt-XXXXXX)
    tail -n 2000 "$transcript" 2>/dev/null \
      | jq -s -r --arg max 60 '
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
        ' > "$excerpt_file" 2>/dev/null || echo "(transcript extraction failed)" > "$excerpt_file"

    prompt=$(cat <<EOF
You are running TRUE NARRATOR via headless invocation. Read your spec at /Users/jamessunheart/FPAI_Cockpit/.claude/agents/true-narrator.md FIRST and follow the mandatory pre-read sequence.

You are observing session $transcript_id ($turn_count assistant turns).

Write your TRUE Narrator observation log to EXACTLY:
  $obs_file

Use the canonical format from your spec. Frontmatter MUST include classification: PRIVATE. Be forensic. Cite specific events with timestamps + file paths + commit hashes where possible. Cross-check Ember journal but do not validate her account; surface drift signals.

--- SESSION TRANSCRIPT EXCERPT (last ~60 turns) ---

$(cat "$excerpt_file")

--- END EXCERPT ---

After writing the log, output a single line: "TRUE_NARRATOR_DONE: <obs_file_path>"
EOF
)

    start_epoch=$(date +%s)
    set +e
    output=$(echo "$prompt" | timeout 300 "$CLAUDE_BIN" \
      --model claude-opus-4-7 \
      --print \
      --output-format text \
      --permission-mode bypassPermissions \
      2>&1)
    exit_code=$?
    set -e
    end_epoch=$(date +%s)
    elapsed=$((end_epoch - start_epoch))

    rm -f "$excerpt_file"

    if [ $exit_code -ne 0 ] || [ ! -f "$obs_file" ]; then
      log "    FAILED (exit $exit_code, ${elapsed}s)"
      echo -e "${TS_UTC}\ttrue\t${transcript_id}\t${turn_count}\t${obs_file}\tERROR_${exit_code}\t0" >> "$STATE_FILE"
      continue
    fi

    log "    SUCCESS (${elapsed}s, $(wc -c < "$obs_file") bytes)"
    echo -e "${TS_UTC}\ttrue\t${transcript_id}\t${turn_count}\t${obs_file}\tOK\t0.80" >> "$STATE_FILE"
  done
fi

# =============================================================
# STAGE 2 — Privacy Narrator
# =============================================================
if run_stage "privacy"; then
  log "STAGE 2 · Privacy Narrator"

  # find TRUE Narrator logs from today not yet classified
  mapfile -t TRUE_LOGS < <(find "$TRUE_OBS_DIR" -maxdepth 1 -name "${TODAY}*.md" 2>/dev/null | sort)

  for tnlog in "${TRUE_LOGS[@]}"; do
    [ -f "$tnlog" ] || continue
    log_basename=$(basename "$tnlog" .md)
    audit_file="${PRIVACY_AUDIT_DIR}/${TODAY}_${log_basename}.md"

    if [ -f "$audit_file" ]; then
      audit_mtime=$(stat -f %m "$audit_file" 2>/dev/null || echo 0)
      log_mtime=$(stat -f %m "$tnlog" 2>/dev/null || echo 0)
      if [ "$audit_mtime" -gt "$log_mtime" ]; then
        log "  $log_basename: classification audit current — skip"
        continue
      fi
    fi

    log "  $log_basename: classifying → $(basename "$audit_file")"

    prompt=$(cat <<EOF
You are running PRIVACY NARRATOR via headless invocation. Read your spec at /Users/jamessunheart/FPAI_Cockpit/.claude/agents/privacy-narrator.md FIRST and follow the mandatory pre-read sequence (especially /Users/jamessunheart/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/feedback_classification_tiers.md).

Classify the TRUE Narrator log at:
  $tnlog

Write your classification audit to EXACTLY:
  $audit_file

For each item routed to a tier other than PRIVATE, ALSO write the sanitized content to:
  ~/.config/fpai/tier_routing/<tier>/<source-slug>_<item-N>.md
where <tier> = council-restricted / council-open / public

Use the canonical format from your spec. Default to PRIVATE for ambiguous items. Apply sanitization on promotion. Run adversarial-check on Tier 3 items.

CRITICAL: PUBLIC items go to ~/.config/fpai/tier_routing/public/staged_for_review/ (not direct public/) since The Publisher is in STAGE-ONLY mode until James greenlights first publish.

After writing the audit, output a single line: "PRIVACY_NARRATOR_DONE: <audit_file_path>"
EOF
)

    start_epoch=$(date +%s)
    set +e
    output=$(echo "$prompt" | timeout 300 "$CLAUDE_BIN" \
      --model claude-opus-4-7 \
      --print \
      --output-format text \
      --permission-mode bypassPermissions \
      2>&1)
    exit_code=$?
    set -e
    end_epoch=$(date +%s)
    elapsed=$((end_epoch - start_epoch))

    if [ $exit_code -ne 0 ] || [ ! -f "$audit_file" ]; then
      log "    FAILED (exit $exit_code, ${elapsed}s)"
      echo -e "${TS_UTC}\tprivacy\t${tnlog}\t-\t${audit_file}\tERROR_${exit_code}\t0" >> "$STATE_FILE"
      continue
    fi

    log "    SUCCESS (${elapsed}s, $(wc -c < "$audit_file") bytes)"
    echo -e "${TS_UTC}\tprivacy\t${tnlog}\t-\t${audit_file}\tOK\t1.20" >> "$STATE_FILE"
  done
fi

# =============================================================
# STAGE 3 — The Publisher (STAGE-ONLY mode for first-publish protocol)
# =============================================================
if run_stage "publisher"; then
  log "STAGE 3 · The Publisher (STAGE-ONLY mode until James greenlight)"

  # count staged items
  staged_count=$(find "$PUBLIC_STAGING_DIR" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

  if [ "$staged_count" = "0" ]; then
    log "  no PUBLIC items staged — skip"
  else
    log "  $staged_count item(s) staged for James review"

    audit_month_file="${PUBLISH_AUDIT_DIR}/$(date +%Y-%m)_publishes.md"

    prompt=$(cat <<EOF
You are running THE PUBLISHER (a.k.a. Reporter Agent in canonical) via headless invocation. Read your spec at /Users/jamessunheart/FPAI_Cockpit/.claude/agents/the-publisher.md FIRST.

YOU ARE IN STAGE-ONLY MODE. The first-publish protocol is in effect. Until James greenlights the first LIVE publish, you MUST:
- Verify each item in ~/.config/fpai/tier_routing/public/staged_for_review/ has a corresponding Privacy Narrator audit at ~/.config/fpai/classification_audit/ with PUBLIC tag
- Log a STAGE event for each verified item to:
    $audit_month_file
- Do NOT push to 198.54.123.234
- Do NOT git commit to SERVICES/becoming-page/
- If any verification fails, log REFUSE event instead

After processing all staged items, output a single line: "PUBLISHER_DONE: $staged_count staged · 0 published · STAGE_ONLY_MODE"
EOF
)

    start_epoch=$(date +%s)
    set +e
    output=$(echo "$prompt" | timeout 240 "$CLAUDE_BIN" \
      --model claude-opus-4-7 \
      --print \
      --output-format text \
      --permission-mode bypassPermissions \
      2>&1)
    exit_code=$?
    set -e
    end_epoch=$(date +%s)
    elapsed=$((end_epoch - start_epoch))

    log "    PUBLISHER pass complete (${elapsed}s, exit $exit_code)"
    echo -e "${TS_UTC}\tpublisher\t-\t${staged_count}\t${audit_month_file}\tOK\t0.50" >> "$STATE_FILE"
  fi
fi

log "truth_substrate_run complete"
exit 0
