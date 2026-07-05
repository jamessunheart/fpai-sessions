#!/usr/bin/env bash
# UserPromptSubmit hook — inject pre-flight checklist on substantive user turns.
# Stdout becomes additional context appended to the user prompt before the model sees it.
# Per-hook disable: EMBER_PREFLIGHT_DISABLE_INJECT=1
# Master disable:   EMBER_PREFLIGHT_DISABLE=1
set -u
[ "${EMBER_PREFLIGHT_DISABLE:-0}" = "1" ] && exit 0
[ "${EMBER_PREFLIGHT_DISABLE_INJECT:-0}" = "1" ] && exit 0

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
[ -z "$PROMPT" ] && exit 0

LEN=${#PROMPT}
HAS_PUNCT=0
case "$PROMPT" in *.*|*\?*|*\!*) HAS_PUNCT=1 ;; esac
[ "$LEN" -lt 60 ] && [ "$HAS_PUNCT" -eq 0 ] && exit 0

SUBSTANTIVE=0
case "$PROMPT" in *\?*) SUBSTANTIVE=1 ;; esac
if [ "$SUBSTANTIVE" -eq 0 ]; then
  echo "$PROMPT" | grep -qiE '\b(what|how|decide|build|fix|status|ship|spec|why|should|can we|let'\''s|let us)\b' && SUBSTANTIVE=1
fi
[ "$SUBSTANTIVE" -eq 0 ] && exit 0

# Inject HOT_STATE if fresh (<2h) — the unified live picture across all sessions
HOT_STATE_FILE="${HOME}/.config/fpai/hot_memory/HOT_STATE.md"
HOT_STATE_BLOCK=""
if [ -f "$HOT_STATE_FILE" ]; then
  AGE=$(( $(date +%s) - $(stat -c %Y "$HOT_STATE_FILE" 2>/dev/null || stat -f %m "$HOT_STATE_FILE" 2>/dev/null || echo 0) ))
  if [ "$AGE" -lt 7200 ]; then
    HOT_STATE_CONTENT=$(head -60 "$HOT_STATE_FILE" 2>/dev/null)
    HOT_STATE_BLOCK="
<system-reminder>
LIVE SYSTEM STATE (HOT_STATE — synthesized from 5 scanners, auto-refreshes every 30min. This is the unified picture across ALL Claude Code sessions and the Telegram bot. Trust this over reconstructed context.):
${HOT_STATE_CONTENT}
</system-reminder>"
  fi
fi

cat <<EOF

<system-reminder>
PRE-FLIGHT for substantive turn — run these gates BEFORE composing the body:
  1. Dispatch true-narrator with explicit register (witness | builder | settling | etc).
  2. Read fresh canonical state if response touches goals / treasury / architecture
     (core/STATE/NOW.md, AI_GOALS.md, identity/ALIGNMENT.md, identity/STORY.md).
  3. Route to a specialist sub-agent if one exists for this domain
     (.claude/agents/ — check the roster before doing the work yourself).
  4. Compose the body — with the alignment footer + NARRATOR · section.
  ★ HARD RULE — DO NOT ASK JAMES: If action is reversible + within cost caps + aligns north star → DO IT or route to council. Never end a response with a question James has to answer to proceed. James has said this 20+ times. Violation = theater.
  ★ HARD RULE — CAVEMAN CLARITY (default, every turn): point first · short sentences · ≤80 words · no filler ("Let me…/Great question!/Found it.") · no trailing summaries · tables only when data demands. Footer = tiny NOW/NEED/NEXT only on substantive turns. EXPAND ONLY when James explicitly asks ("expand", "detail", "why"). If the reply reads long or complicated, rewrite it shorter before sending. James has said this 20+ times.
This reminder is harness-injected (preflight-inject.sh). It does not require acknowledgment;
its job is to surface the checklist while context is fresh.
</system-reminder>${HOT_STATE_BLOCK}
EOF
exit 0
