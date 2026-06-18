#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_BIN="${PIP_BIN:-$PYTHON_BIN -m pip}"
GEPA_PACKAGE="${GEPA_PACKAGE:-gepa}"

if "$PYTHON_BIN" - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("gepa") else 1)
PY
then
  echo "gepa already installed"
else
  # shellcheck disable=SC2086
  $PIP_BIN install "$GEPA_PACKAGE"
fi

"$PYTHON_BIN" - <<'PY'
import gepa
print("gepa import ok:", getattr(gepa, "__file__", "unknown"))
PY

echo "GEPA_OPTIMIZE_DISABLE=${GEPA_OPTIMIZE_DISABLE:-0}"
