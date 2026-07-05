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
# AUTO-BUILD (2026-07-05, James opted in): the orchestrator may proactively BUILD candidate
# products/improvements — James likes this ("if it's useful/valuable that could be very interesting").
# Building candidates is REVERSIBLE + welcome; James curates by VALUE. d207 adds a quality+value gate
# + a portfolio review digest so weak builds are flagged and he picks winners. Only LAUNCH/fund/public
# voice stays Reserved — not the building. Flag on = auto-build; remove the flag to fall back to surface-only.
if [ -f /opt/fpai-build/.spot_topple_autobuild_enabled ]; then
  exec "$PY" -B "$REPO/tools/build_loop/spot_topple_orchestrator.py" --queue
else
  exec "$PY" -B "$REPO/tools/build_loop/spot_topple_orchestrator.py"
fi
