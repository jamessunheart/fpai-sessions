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

"$PYTHON_BIN" "$PROJECT_DIR/tools/continuity/detect_correction.py" >/dev/null 2>&1 || true
exit 0
