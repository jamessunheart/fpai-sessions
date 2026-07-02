#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}"

cd "$REPO_ROOT"
python3 -B -m tools.build_loop.d011_reality_repair \
  --repo-root "$REPO_ROOT" \
  --ops-ledger "$OPS_LEDGER"
