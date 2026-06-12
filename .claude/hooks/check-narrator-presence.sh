#!/usr/bin/env bash
# Stop hook — verify narrator entry is present, sized correctly, and positioned
# inside the alignment block at the closing position before bottom border.
# Per-hook disable: EMBER_PREFLIGHT_DISABLE_NARRATOR=1
# Master disable:   EMBER_PREFLIGHT_DISABLE=1
set -u
# 2026-06-12: James simplified footer to NEXT + WHY only — narrator no longer required.
[ "${EMBER_PREFLIGHT_DISABLE:-0}" = "1" ] && exit 0
exit 0  # narrator check disabled per James 2026-06-12

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
  # 2026-05-30 (James + GPT): narrator overhead reduced. A SHORT inline narrator
  # (≥12 words, written by Ember — no agent dispatch) is fine on routine turns.
  # Dispatch the full true-narrator agent only on SUBSTANTIVE MILESTONES (builds,
  # decisions, shipped work). See feedback_narrator_substantive_only.md.
  if [ "$WC" -lt 12 ]; then
    FAIL_REASON="NARRATOR · body too short ($WC words; need ≥12 — a one-line inline narrator is enough)"
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
  echo "Required: a NARRATOR · line INSIDE the alignment block (before the closing border)."
  echo "Routine turn → write a SHORT inline narrator (1–2 sentences, ≥12 words) yourself."
  echo "Substantive milestone → dispatch true-narrator for the fuller entry."
  echo ""
  echo "Self-correct on next reply:"
  echo "  1. Add a 'NARRATOR ·' line inside the block (inline is fine)"
  echo "  2. Confirm closing border ─────────────── follows"
  echo ""
  echo "Override (one-shot): EMBER_PREFLIGHT_DISABLE_NARRATOR=1"
} >&2
exit 2
