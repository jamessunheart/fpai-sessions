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
# INTERIM SAFETY (2026-07-05): --queue removed → orchestrator is SURFACE-ONLY (spots + proposes,
# never auto-builds). It auto-built a net-new product (d205 AI Voice Receptionist) with no human
# input — exceeding the Constitution's Reserved-direction line. Re-add --queue only after d207
# scopes auto-topple to reversible IMPROVEMENTS of live things (new products/direction → surface).
# Re-enable with the flag file once d207 lands:
if [ -f /opt/fpai-build/.spot_topple_autobuild_enabled ]; then
  exec "$PY" -B "$REPO/tools/build_loop/spot_topple_orchestrator.py" --queue
else
  exec "$PY" -B "$REPO/tools/build_loop/spot_topple_orchestrator.py"
fi
