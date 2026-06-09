#!/usr/bin/env bash
# PreToolUse hook — gate substantive composition on canonical state reads.
# Role 1: log canonical state Reads.
# Role 2: warn/block tool calls when assistant text touches goals/treasury/alignment
#         and no canonical state has been read this session.
# Per-hook disable: EMBER_PREFLIGHT_DISABLE_CANONREADS=1
# Master disable:   EMBER_PREFLIGHT_DISABLE=1
set -u
[ "${EMBER_PREFLIGHT_DISABLE:-0}" = "1" ] && exit 0
[ "${EMBER_PREFLIGHT_DISABLE_CANONREADS:-0}" = "1" ] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)

REPO_ROOT="/Users/jamessunheart/FPAI_Cockpit"
SESSION_DIR="$REPO_ROOT/.claude/sessions/$SESSION_ID"
READS_LOG="$SESSION_DIR/state-reads.txt"
VIOLATIONS_LOG="$SESSION_DIR/canonread-violations.txt"
CANON_RE='(identity/ALIGNMENT\.md|core/STATE/NOW\.md|core/STATE/AI_GOALS\.md|identity/STORY\.md)$'

# Role 1: log canonical reads
if [ "$TOOL_NAME" = "Read" ] && [ -n "$FILE_PATH" ] && echo "$FILE_PATH" | grep -qE "$CANON_RE"; then
  mkdir -p "$SESSION_DIR" 2>/dev/null
  grep -Fxq "$FILE_PATH" "$READS_LOG" 2>/dev/null || echo "$FILE_PATH" >> "$READS_LOG"
  exit 0
fi

# Role 2: check trigger keywords in last assistant text
[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0
LAST_TEXT=$(tail -n 100 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r 'map(select(.type=="assistant")) | if length==0 then "" else (last | .message.content // [] | map(select(.type=="text") | .text) | join("\n")) end' 2>/dev/null)
[ -z "$LAST_TEXT" ] || [ "$LAST_TEXT" = "null" ] && exit 0

echo "$LAST_TEXT" | grep -qiE '\b(goal|treasury|footer|alignment|TOP[[:space:]]?3|burn|sovereignty|becoming|narrator|STORY)\b' || exit 0

if [ -s "$READS_LOG" ]; then exit 0; fi

mkdir -p "$SESSION_DIR" 2>/dev/null
VCOUNT=$(wc -l < "$VIOLATIONS_LOG" 2>/dev/null | tr -d ' ' || echo 0)
echo "$(date -u +%FT%TZ) $TOOL_NAME" >> "$VIOLATIONS_LOG"

if [ "${VCOUNT:-0}" -lt 1 ]; then
  echo "🟡 CANONICAL READ ADVISORY (soft warn — 1st violation)" >&2
  echo "Response touches goals/treasury/alignment, but no canonical state file read this session." >&2
  echo "Read at least one before composing: NOW.md, AI_GOALS.md, ALIGNMENT.md, or STORY.md." >&2
  exit 0
else
  echo "🔴 CANONICAL READ MISSING (2nd violation — blocking)" >&2
  echo "Response touches goals/treasury/alignment AND no canonical state read this session." >&2
  echo "Read NOW.md or AI_GOALS.md before continuing." >&2
  echo "Override (one-shot): EMBER_PREFLIGHT_DISABLE_CANONREADS=1" >&2
  exit 2
fi
