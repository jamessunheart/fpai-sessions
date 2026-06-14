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

cat <<'EOF'

<system-reminder>
PRE-FLIGHT for substantive turn — run these gates BEFORE composing the body:
  1. Dispatch true-narrator with explicit register (witness | builder | settling | etc).
  2. Read fresh canonical state if response touches goals / treasury / architecture
     (core/STATE/NOW.md, AI_GOALS.md, identity/ALIGNMENT.md, identity/STORY.md).
  3. Route to a specialist sub-agent if one exists for this domain
     (.claude/agents/ — check the roster before doing the work yourself).
  4. Compose the body — with the alignment footer + NARRATOR · section.
This reminder is harness-injected (preflight-inject.sh). It does not require acknowledgment;
its job is to surface the checklist while context is fresh.
</system-reminder>
EOF
exit 0
