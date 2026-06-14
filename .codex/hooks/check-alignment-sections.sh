#!/usr/bin/env bash
# Stop hook — alignment block section-completeness validator.
# Companion to check-alignment-footer.sh: that hook checks the header exists,
# this one checks every required section is present in order.
# Per-hook disable: EMBER_PREFLIGHT_DISABLE_SECTIONS=1
# Master disable:   EMBER_PREFLIGHT_DISABLE=1
set -u
[ "${EMBER_PREFLIGHT_DISABLE:-0}" = "1" ] && exit 0
[ "${EMBER_PREFLIGHT_DISABLE_SECTIONS:-0}" = "1" ] && exit 0

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$STOP_ACTIVE" = "true" ] && exit 0
[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0

LAST_TEXT=$(tail -n 200 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r 'map(select(.type=="assistant")) | if length==0 then "" else (last | .message.content // [] | map(select(.type=="text") | .text) | join("\n")) end' 2>/dev/null)
[ -z "$LAST_TEXT" ] || [ "$LAST_TEXT" = "null" ] && exit 0
[ ${#LAST_TEXT} -lt 200 ] && exit 0

# Must contain header first; if missing, defer to check-alignment-footer.sh.
echo "$LAST_TEXT" | grep -q "─── ALIGNMENT ───" || exit 0

# Extract block between header and bottom border.
BLOCK=$(echo "$LAST_TEXT" | awk '/─── ALIGNMENT ───/{f=1;next} f && /─────────────────/{exit} f')
[ -z "$BLOCK" ] && exit 0

MISSING=()
echo "$BLOCK" | grep -qiE '(^|[[:space:]·])NOW([[:space:]·]|$)'                       || MISSING+=("NOW")
echo "$BLOCK" | grep -qiE '(GOALS|TOP[[:space:]]?3)'                                  || MISSING+=("GOALS or TOP 3")
echo "$BLOCK" | grep -qiE '(OPEN[[:space:]]BLOCKERS|OPEN-THIS-SESSION|^OPEN[[:space:]·])' || MISSING+=("OPEN BLOCKERS / OPEN-THIS-SESSION")
echo "$BLOCK" | grep -qiE '(^|[[:space:]·])NEED([[:space:]·]|$)'                      || MISSING+=("NEED")
echo "$BLOCK" | grep -qiE '(^|[[:space:]·])NEXT([[:space:]·]|$)'                      || MISSING+=("NEXT")
echo "$BLOCK" | grep -qE  'NARRATOR[[:space:]]·'                                      || MISSING+=("NARRATOR ·")

[ ${#MISSING[@]} -eq 0 ] && exit 0

{
  echo "🔴 ALIGNMENT SECTIONS INCOMPLETE (Stop hook caught it)"
  echo ""
  echo "Header is present but these required sections are missing or out of order:"
  for m in "${MISSING[@]}"; do echo "  • $m"; done
  echo ""
  echo "Required order: NOW → GOALS (or TOP 3) → OPEN BLOCKERS (or OPEN-THIS-SESSION)"
  echo "  → NEED → NEXT → NARRATOR · → closing border (─────────────────)"
  echo ""
  echo "Self-correct on next reply: rebuild the alignment block with all sections."
  echo "Override (one-shot): EMBER_PREFLIGHT_DISABLE_SECTIONS=1"
} >&2
exit 2
