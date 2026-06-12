#!/usr/bin/env bash
# sovereign_chat.sh — single entrypoint for sovereign AI inference
# Routes prompts to local Ollama (32B-class default) or remote rental endpoint (70B-class).
#
# Usage:
#   sovereign_chat.sh "your prompt"                      # default: local 32B
#   sovereign_chat.sh --model qwen2.5-coder:32b "..."    # explicit local model
#   sovereign_chat.sh --tier 70b "..."                   # routes to remote 70B endpoint
#   sovereign_chat.sh --tier fast "..."                  # llama3.1:8b for routine
#   echo "prompt" | sovereign_chat.sh                    # stdin input
#
# Environment overrides:
#   SOVEREIGN_LOCAL_URL    default http://localhost:11434
#   SOVEREIGN_REMOTE_URL   default unset (set after Day 3-4 H100 rental)
#   SOVEREIGN_REMOTE_KEY   bearer for remote endpoint
#   SOVEREIGN_LOG          default ~/.config/fpai/sovereign_phase1/calls.log
#
# Exit codes:
#   0  success
#   1  no input
#   2  endpoint unreachable
#   3  model not available
#   4  bad args
#
# Phase 1 reversibility: this script is the ONLY entrypoint Ember / agents use for
# sovereign calls. To kill the sovereign track entirely, rename this file or
# `chmod -x` it; nothing else changes.

set -euo pipefail

LOCAL_URL="${SOVEREIGN_LOCAL_URL:-http://localhost:11434}"
REMOTE_URL="${SOVEREIGN_REMOTE_URL:-}"
REMOTE_KEY="${SOVEREIGN_REMOTE_KEY:-}"
LOG_FILE="${SOVEREIGN_LOG:-$HOME/.config/fpai/sovereign_phase1/calls.log}"
mkdir -p "$(dirname "$LOG_FILE")"

# Defaults — overridden by --model or --tier
MODEL="qwen2.5-coder:32b-instruct-q4_K_M"   # ~18GB on 24GB unified mem · fits M4
TIER="local"

usage() {
  sed -n '2,20p' "$0"
  exit 4
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)    MODEL="$2"; TIER="local"; shift 2 ;;
    --tier)
      case "$2" in
        fast)   MODEL="llama3.1:8b"; TIER="local" ;;
        32b)    MODEL="qwen2.5-coder:32b-instruct-q4_K_M"; TIER="local" ;;
        70b)    MODEL="llama3.3:70b-instruct"; TIER="remote" ;;
        *)      echo "unknown tier: $2" >&2; exit 4 ;;
      esac
      shift 2
      ;;
    -h|--help)  usage ;;
    *)          PROMPT="$1"; shift ;;
  esac
done

# Read stdin if no prompt arg
if [[ -z "${PROMPT:-}" ]]; then
  if [[ -t 0 ]]; then
    echo "error: no prompt given (arg or stdin)" >&2
    exit 1
  fi
  PROMPT="$(cat)"
fi
[[ -z "$PROMPT" ]] && { echo "error: empty prompt" >&2; exit 1; }

call_local() {
  # Health check
  if ! curl -fsS --max-time 3 "$LOCAL_URL/api/tags" >/dev/null 2>&1; then
    echo "error: local Ollama unreachable at $LOCAL_URL (is 'ollama serve' running?)" >&2
    exit 2
  fi
  # Verify model present
  if ! curl -fsS "$LOCAL_URL/api/tags" 2>/dev/null | grep -q "\"name\":\"$MODEL\""; then
    echo "error: model '$MODEL' not pulled. Run: ollama pull $MODEL" >&2
    exit 3
  fi
  # Generate (non-streaming for caveman clarity in script consumers)
  curl -fsS --max-time 600 "$LOCAL_URL/api/generate" \
    -H "Content-Type: application/json" \
    -d "$(jq -nc --arg m "$MODEL" --arg p "$PROMPT" \
           '{model:$m, prompt:$p, stream:false}')" \
    | jq -r '.response'
}

call_remote() {
  if [[ -z "$REMOTE_URL" ]]; then
    echo "error: SOVEREIGN_REMOTE_URL not set (Day 3-4 rental not stood up yet)" >&2
    exit 2
  fi
  # OpenAI-compat chat completions shape (vLLM / TGI / most rental endpoints)
  curl -fsS --max-time 600 "$REMOTE_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${REMOTE_KEY}" \
    -d "$(jq -nc --arg m "$MODEL" --arg p "$PROMPT" \
           '{model:$m, messages:[{role:"user",content:$p}], stream:false}')" \
    | jq -r '.choices[0].message.content'
}

START_TS="$(date -u +%FT%TZ)"
START_EPOCH="$(date +%s)"

case "$TIER" in
  local)  RESPONSE="$(call_local)" ;;
  remote) RESPONSE="$(call_remote)" ;;
esac

END_EPOCH="$(date +%s)"
DUR=$(( END_EPOCH - START_EPOCH ))

# Log every call (cost = $0 local, $X remote — tracked separately Day 7)
{
  printf '{"ts":"%s","tier":"%s","model":"%s","dur_s":%d,"prompt_chars":%d,"resp_chars":%d}\n' \
    "$START_TS" "$TIER" "$MODEL" "$DUR" "${#PROMPT}" "${#RESPONSE}"
} >> "$LOG_FILE"

printf '%s\n' "$RESPONSE"
