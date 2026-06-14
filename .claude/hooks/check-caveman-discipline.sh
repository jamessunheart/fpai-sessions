#!/usr/bin/env bash
# Stop hook — caveman-discipline line-count enforcement.
#
# Catches the footer-wall regression (narrator 2026-05-21 turn 20): replies
# accumulate sub-blocks until the user can't see the answer for the wall.
# VOICE.md said caveman two days ago. No hook counted lines. This is the
# counter.
#
# Reads thresholds from ~/.config/fpai/voice/caveman_thresholds.json.
# Counts body lines (above ─── ALIGNMENT ─── header) and footer lines
# (between header and bottom border ─────────────────).
#
# Soft-warn (exit 0 + stderr) when body > body_soft_warn_lines OR
#                                  footer > footer_soft_warn_lines.
# Hard-warn (exit 2) when body > body_hard_block_lines AND no [LONG-FORM]
#                    tag at top of reply.
#
# Kill switches (priority order):
#   1. EMBER_CAVEMAN_HOOK_DISABLE=1   one-shot env disable
#   2. EMBER_PREFLIGHT_DISABLE=1       master Stop-hook disable
#   3. rm ~/.config/fpai/voice/caveman_thresholds.json  graceful bail
#   4. Remove from .claude/settings.json Stop array
#
# Spec: ~/.config/fpai/hook_specs/check-caveman-discipline_v1.md
# Work-order: ~/.config/fpai/forge/queued/done/2026-05-21_1500_caveman-line-count-hook.md

set -u

# Kill switches
[ "${EMBER_PREFLIGHT_DISABLE:-0}" = "1" ] && exit 0
[ "${EMBER_CAVEMAN_HOOK_DISABLE:-0}" = "1" ] && exit 0

CFG="${HOME}/.config/fpai/voice/caveman_thresholds.json"
[ ! -f "$CFG" ] && exit 0   # graceful bail if config absent

# Load thresholds (jq; fall back to defaults if any field missing or jq fails)
BODY_SOFT=$(jq -r '.body_soft_warn_lines // 60' "$CFG" 2>/dev/null)
BODY_HARD=$(jq -r '.body_hard_block_lines // 120' "$CFG" 2>/dev/null)
FOOTER_SOFT=$(jq -r '.footer_soft_warn_lines // 150' "$CFG" 2>/dev/null)
LONG_FORM_TAG=$(jq -r '.long_form_tag // "[LONG-FORM]"' "$CFG" 2>/dev/null)
MIN_CHARS=$(jq -r '.min_response_chars // 200' "$CFG" 2>/dev/null)

# Validate numerics; if jq returned junk, bail safely.
case "$BODY_SOFT$BODY_HARD$FOOTER_SOFT$MIN_CHARS" in
  *[!0-9]*) exit 0 ;;
esac

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)

# Loop protection + sanity
[ "$STOP_ACTIVE" = "true" ] && exit 0
[ -z "$TRANSCRIPT" ] && exit 0
[ ! -f "$TRANSCRIPT" ] && exit 0

# Pull last assistant message text
LAST_TEXT=$(tail -n 200 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r 'map(select(.type=="assistant"))
              | if length == 0 then ""
                else (last | .message.content // []
                      | map(select(.type=="text") | .text) | join("\n"))
                end' 2>/dev/null)

[ -z "$LAST_TEXT" ] && exit 0
[ "$LAST_TEXT" = "null" ] && exit 0

# Triviality bypass
LEN=${#LAST_TEXT}
[ "$LEN" -lt "$MIN_CHARS" ] && exit 0

# Detect [LONG-FORM] tag in first 5 lines of reply
HEAD5=$(printf '%s\n' "$LAST_TEXT" | head -n 5)
HAS_LONG_FORM=0
echo "$HEAD5" | grep -qF "$LONG_FORM_TAG" && HAS_LONG_FORM=1

# Split body vs footer.
# Body = lines above the ─── ALIGNMENT ─── header.
# Footer = lines from header through bottom border ─────────────────.
# If no alignment header found, treat entire reply as body, footer=0.
HEADER_LINE=$(printf '%s\n' "$LAST_TEXT" | grep -n '─── ALIGNMENT ───' | head -n 1 | cut -d: -f1)

TOTAL_LINES=$(printf '%s\n' "$LAST_TEXT" | wc -l | tr -d ' ')

if [ -z "$HEADER_LINE" ]; then
  BODY_LINES="$TOTAL_LINES"
  FOOTER_LINES=0
else
  BODY_LINES=$((HEADER_LINE - 1))
  # Footer: from header line to (and including) bottom border
  FOOTER_END=$(printf '%s\n' "$LAST_TEXT" | awk -v start="$HEADER_LINE" '
    NR >= start {
      if (NR > start && /─────────────────/) { print NR; exit }
    }')
  if [ -z "$FOOTER_END" ]; then
    FOOTER_LINES=$((TOTAL_LINES - HEADER_LINE + 1))
  else
    FOOTER_LINES=$((FOOTER_END - HEADER_LINE + 1))
  fi
fi

# Decide warnings
SOFT_BODY=0; SOFT_FOOTER=0; HARD_BODY=0
[ "$BODY_LINES" -gt "$BODY_SOFT" ] && SOFT_BODY=1
[ "$FOOTER_LINES" -gt "$FOOTER_SOFT" ] && SOFT_FOOTER=1
if [ "$BODY_LINES" -gt "$BODY_HARD" ] && [ "$HAS_LONG_FORM" -eq 0 ]; then
  HARD_BODY=1
fi

# Hard block path
if [ "$HARD_BODY" -eq 1 ]; then
  {
    echo "🔴 caveman-drift HARD (Stop hook caught it)"
    echo ""
    echo "  body=${BODY_LINES} lines (hard threshold: ${BODY_HARD})"
    echo "  footer=${FOOTER_LINES} lines (soft threshold: ${FOOTER_SOFT})"
    echo ""
    echo "VOICE.md says caveman: short sentences, point first, ≤80 words default."
    echo "The user cannot see the answer for the wall."
    echo ""
    echo "Self-correct on next reply (pick one):"
    echo "  (a) Strengthen the message: cut to ≤60 body lines, lead with the answer"
    echo "  (b) If genuinely long-form work: add ${LONG_FORM_TAG} as the FIRST line"
    echo "      of the reply to mark intent and bypass this block"
    echo ""
    echo "Override (one-shot): EMBER_CAVEMAN_HOOK_DISABLE=1"
    echo "Spec: ~/.config/fpai/hook_specs/check-caveman-discipline_v1.md"
  } >&2
  exit 2
fi

# Soft-warn path (one combined message if both)
if [ "$SOFT_BODY" -eq 1 ] || [ "$SOFT_FOOTER" -eq 1 ]; then
  {
    echo "🟡 caveman-drift (Stop hook noted it)"
    echo ""
    echo "  body=${BODY_LINES} lines (soft threshold: ${BODY_SOFT})"
    echo "  footer=${FOOTER_LINES} lines (soft threshold: ${FOOTER_SOFT})"
    echo ""
    echo "VOICE.md says ≤80 words default. Strengthen the message OR shrink the footer."
    echo "Soft-warn only — reply already shipped. Tune next turn."
  } >&2
  exit 0
fi

exit 0
