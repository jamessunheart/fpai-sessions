#!/usr/bin/env bash
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
BRAIN="${FPAI_BRAIN_ROOT:-/opt/sh-brain-src}"
PY="${PYTHON:-$BRAIN/.venv/bin/python}"
ENVFILE="${FPAI_CURATOR_ENV:-/etc/sh-brain/curator.env}"

[ -f /opt/fpai-build/.spot_topple_disabled ] && {
  echo "spot-topple disabled by /opt/fpai-build/.spot_topple_disabled"
  exit 0
}

if [ -f "$ENVFILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENVFILE" 2>/dev/null || true
  set +a
fi

if [ ! -x "$PY" ]; then
  PY=python3
fi

cd "$REPO"
exec "$PY" -B "$REPO/tools/build_loop/spot_topple_orchestrator.py" --queue
