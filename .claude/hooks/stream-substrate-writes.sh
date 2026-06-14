#!/usr/bin/env bash
# PostToolUse hook · streams substrate writes to TG (Phase 1 brain → TG pipeline).
#
# Watches for writes to:
#   - identity/sessions/YYYY-MM-DD_*.md            → journal (when ## JOURNAL section grows)
#   - memory/{feedback,project,reference}_*.md     → canonical save
#   - identity/{ALIGNMENT,STORY,EMBER_GOALS}.md    → alignment shift
#   - memory/observations/narrator/*.md            → narrator log
#   - memory/observations/meta_narrator/*.md       → meta-narrator audit
#
# Triggers `stream_to_tg.sh` with appropriate category/severity/classification.
# Always non-blocking; failures are silent (logged in stream.log).
#
# Reversibility:
#   - Remove from .claude/settings.json PostToolUse list → hook stops firing
#   - chmod -x this file → hook fails open (no stream, no harm)

set -u

INPUT=$(cat 2>/dev/null || echo "{}")
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

STREAM_SCRIPT="${HOME}/FPAI_Cockpit/infra/scripts/stream_to_tg.sh"
[ -x "$STREAM_SCRIPT" ] || exit 0

# Honor a global kill-switch env var (useful during heavy build sessions)
[ "${TG_STREAM_DISABLE:-0}" = "1" ] && exit 0

# Per-file debounce · don't re-stream same file within 60s
DEBOUNCE_DIR="${HOME}/.config/fpai/tg_stream/debounce"
mkdir -p "$DEBOUNCE_DIR"

MEMORY_BASE="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory"

# Only act on writes inside memory base
case "$FILE_PATH" in
  "$MEMORY_BASE"/*) ;;
  *) exit 0 ;;
esac

REL="${FILE_PATH#$MEMORY_BASE/}"
BASENAME=$(basename "$FILE_PATH")

# Debounce check: skip if streamed within last 60s
DEBOUNCE_KEY=$(echo "$FILE_PATH" | shasum -a 1 | cut -c1-16)
DEBOUNCE_FILE="${DEBOUNCE_DIR}/${DEBOUNCE_KEY}"
if [ -f "$DEBOUNCE_FILE" ]; then
  last_epoch=$(stat -f %m "$DEBOUNCE_FILE" 2>/dev/null || stat -c %Y "$DEBOUNCE_FILE" 2>/dev/null || echo 0)
  age=$(( $(date +%s) - last_epoch ))
  [ "$age" -lt 60 ] && exit 0
fi

stream() {
  # stream <category> <severity> <body> [link]
  local cat="$1" sev="$2" body="$3" link="${4:-}"
  touch "$DEBOUNCE_FILE"
  "$STREAM_SCRIPT" \
    --category="$cat" \
    --severity="$sev" \
    --classification=PRIVATE \
    --body="$body" \
    --link="$link" \
    >/dev/null 2>&1 &
  disown 2>/dev/null || true
}

# ---- Narrator obs log -------------------------------------------------
# (Note: narrator_run.sh streams these too · this hook fires when manual edits
# touch them. De-dup is mild — TG may receive 2 messages but they're labeled.)
case "$REL" in
  observations/narrator/*.md)
    summary=$(awk '/^---$/{f++;next} f<2{next} /^#/{next} /^[[:space:]]*$/{next} {print; exit}' "$FILE_PATH" 2>/dev/null | head -c 200)
    [ -z "$summary" ] && summary="Narrator log saved"
    stream "narrator" "med" "Narrator: $summary" "$BASENAME"
    exit 0
    ;;
  observations/meta_narrator/*.md)
    verdict=$(grep -oE '(HIGH FIDELITY|MINOR DRIFT|MATERIAL DRIFT|INSUFFICIENT GROUND TRUTH)' "$FILE_PATH" | head -1 || echo UNKNOWN)
    stream "meta-narrator" "med" "Meta-Narrator audit saved · verdict=$verdict" "$BASENAME"
    exit 0
    ;;
esac

# ---- Episodic session file (journal stream) ---------------------------
# Fire only when the file contains a ## JOURNAL section · stream the LAST journal entry.
case "$REL" in
  identity/sessions/*.md)
    # Extract the last entry after "## JOURNAL" heading
    journal_block=$(awk '/^## JOURNAL/,0' "$FILE_PATH" 2>/dev/null)
    [ -z "$journal_block" ] && exit 0
    # Last journal entry · take last non-empty paragraph
    last_entry=$(echo "$journal_block" | awk '/^[^#]/ && NF { last=$0 } END { print last }' | head -c 220)
    [ -z "$last_entry" ] && exit 0
    stream "journal" "med" "$last_entry" "$BASENAME"
    exit 0
    ;;
esac

# ---- Canonical save (feedback / project / reference) ------------------
case "$BASENAME" in
  feedback_*.md|project_*.md|reference_*.md)
    # Pull description from frontmatter if present
    desc=$(awk '/^description:/{sub(/^description: *"?/,""); sub(/"? *$/,""); print; exit}' "$FILE_PATH" 2>/dev/null | head -c 180)
    [ -z "$desc" ] && desc="$BASENAME saved"
    stream "canonical" "med" "canonized: $BASENAME · $desc" "$BASENAME"
    exit 0
    ;;
esac

# ---- Alignment shift (ALIGNMENT.md / STORY.md / EMBER_GOALS.md) -------
case "$REL" in
  identity/ALIGNMENT.md)
    stream "alignment" "med" "ALIGNMENT refreshed · standing contract updated" "ALIGNMENT.md"
    exit 0
    ;;
  identity/STORY.md)
    stream "alignment" "low" "STORY.md updated · chapter handoff refreshed" "STORY.md"
    exit 0
    ;;
  identity/EMBER_GOALS.md)
    stream "alignment" "med" "EMBER_GOALS refreshed · becoming objectives updated" "EMBER_GOALS.md"
    exit 0
    ;;
esac

exit 0
