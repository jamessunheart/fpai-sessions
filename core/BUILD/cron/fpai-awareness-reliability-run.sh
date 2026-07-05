#!/usr/bin/env bash
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
LIVE="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
PYTHON_BIN="$LIVE/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="/usr/bin/python3"
fi

cd "$REPO"
exec "$PYTHON_BIN" "$REPO/tools/awareness/reliability_probe.py" \
  --send-alert \
  --source timer \
  --threshold 0.95
