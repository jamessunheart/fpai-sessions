#!/usr/bin/env bash
# critique.sh — CLI front-end for legal-critic
# Usage:
#   ./critique.sh <markdown-file> [focus-area]
#   echo "doc text" | ./critique.sh - [focus-area]
set -euo pipefail

ENDPOINT="${LEGAL_CRITIC_URL:-https://brain.sunheart.com/legal/critique}"
TOKEN_FILE="${FPAI_AI_TOKEN_FILE:-$HOME/.config/fpai/ai.token}"
TOKEN="${LEGAL_CRITIC_TOKEN:-$(cat "$TOKEN_FILE" 2>/dev/null || true)}"

if [ -z "${TOKEN:-}" ]; then
  echo "error: set LEGAL_CRITIC_TOKEN or write a token to $TOKEN_FILE" >&2
  exit 1
fi

if [ $# -lt 1 ]; then
  echo "usage: $0 <markdown-file|-> [focus-area]" >&2
  exit 2
fi

INPUT="$1"
FOCUS="${2:-}"

if [ "$INPUT" = "-" ]; then
  DOC=$(cat)
else
  DOC=$(cat "$INPUT")
fi

PAYLOAD=$(jq -nc --arg doc "$DOC" --arg focus "$FOCUS" \
  'if $focus == "" then {doc_text:$doc} else {doc_text:$doc, focus:$focus} end')

curl -sS -X POST "$ENDPOINT" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data "$PAYLOAD" \
| jq -r '.critique_md'
