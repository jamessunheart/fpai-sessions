#!/usr/bin/env bash
# Claude Code UserPromptSubmit hook: capture James correction turns.
# Non-blocking by design; hook failures must never stop Claude Code.
set +e

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}}"

PYTHON_BIN="${FPAI_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for _candidate in /opt/sh-brain-src/.venv/bin/python3 /opt/sh-brain-src/.venv/bin/python python3; do
    if command -v "$_candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$_candidate"
      break
    fi
  done
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

# If DB env file is local, run directly. Otherwise relay via SSH to server 162.
if [[ -f /etc/sh-brain/curator.env ]]; then
  "$PYTHON_BIN" "$PROJECT_DIR/tools/continuity/detect_correction.py" >/dev/null 2>&1 || true
else
  # Laptop/remote surface: pipe stdin + env vars to server 162 where the DB lives
  PROMPT="${CLAUDE_USER_PROMPT:-}"
  SESSION="${CLAUDE_SESSION_ID:-unknown}"
  if [[ -n "$PROMPT" ]]; then
    ssh -o BatchMode=yes -o ConnectTimeout=3 root@162.0.208.88 \
      "CLAUDE_USER_PROMPT=$(printf '%q' "$PROMPT") CLAUDE_SESSION_ID=$(printf '%q' "$SESSION") \
       /opt/sh-brain-src/.venv/bin/python3 /opt/fpai-build/FPAI_Cockpit/tools/continuity/detect_correction.py" \
      >/dev/null 2>&1 || true
  fi
fi
exit 0
