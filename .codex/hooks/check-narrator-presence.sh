#!/usr/bin/env bash
# Stop hook — verify narrator entry is present, sized correctly, and positioned
# inside the alignment block at the closing position before bottom border.
# Per-hook disable: EMBER_PREFLIGHT_DISABLE_NARRATOR=1
# Master disable:   EMBER_PREFLIGHT_DISABLE=1
set -u
[ "${EMBER_PREFLIGHT_DISABLE:-0}" = "1" ] && exit 0
[ "${EMBER_PREFLIGHT_DISABLE_NARRATOR:-0}" = "1" ] && exit 0

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$STOP_ACTIVE" = "true" ] && exit 0
[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0

LAST_TEXT=$(tail -n 200 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r 'map(select(.type=="assistant")) | if length==0 then "" else (last | .message.content // [] | map(select(.type=="text") | .text) | join("\n")) end' 2>/dev/null)
[ -z "$LAST_TEXT" ] || [ "$LAST_TEXT" = "null" ] && exit 0
[ ${#LAST_TEXT} -lt 200 ] && exit 0
echo "$LAST_TEXT" | grep -q "─── ALIGNMENT ───" || exit 0

BLOCK=$(echo "$LAST_TEXT" | awk '/─── ALIGNMENT ───/{f=1;next} f && /─────────────────/{exit} f')

FAIL_REASON=""
if [ -z "$BLOCK" ]; then
  FAIL_REASON="alignment block empty or no closing border"
elif ! echo "$BLOCK" | grep -qE 'NARRATOR[[:space:]]·'; then
  if echo "$LAST_TEXT" | grep -qE 'NARRATOR[[:space:]]·'; then
    FAIL_REASON="NARRATOR · section found OUTSIDE alignment block — must be INSIDE before closing border"
  else
    FAIL_REASON="NARRATOR · section missing entirely"
  fi
else
  NARR_BODY=$(echo "$BLOCK" | awk '/NARRATOR[[:space:]]·/{f=1} f' | sed '1d')
  WC=$(echo "$NARR_BODY" | tr -s '[:space:]' '\n' | grep -cE '\S')
  if [ "$WC" -lt 100 ]; then
    FAIL_REASON="NARRATOR · body too short ($WC words; need 100–200)"
  elif [ "$WC" -gt 220 ]; then
    FAIL_REASON="NARRATOR · body too long ($WC words; cap 200, hard ceiling 220)"
  fi
fi

[ -z "$FAIL_REASON" ] && exit 0

{
  echo "🔴 NARRATOR PRESENCE CHECK FAILED (Stop hook caught it)"
  echo ""
  echo "Reason: $FAIL_REASON"
  echo ""
  echo "Required: dispatch true-narrator and surface verbatim entry INSIDE alignment"
  echo "block at closing position before bottom border. 100–200 words verbatim."
  echo ""
  echo "Self-correct on next reply:"
  echo "  1. One-line ack the hook caught it"
  echo "  2. Dispatch true-narrator (Task tool, agent: true-narrator)"
  echo "  3. Place the verbatim entry under 'NARRATOR ·' inside the block"
  echo "  4. Confirm closing border ─────────────── follows"
  echo ""
  echo "Override (one-shot): EMBER_PREFLIGHT_DISABLE_NARRATOR=1"
} >&2
exit 2
