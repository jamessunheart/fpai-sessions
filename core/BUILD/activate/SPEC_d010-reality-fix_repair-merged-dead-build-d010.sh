#!/usr/bin/env bash
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}"
PYTHON="${PYTHON:-python3}"

cd "$REPO"
"$PYTHON" -m tools.build_loop.d010_reality_repair \
  --repo-root "$REPO" \
  --ops-ledger "$OPS_LEDGER"
