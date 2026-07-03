#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}"

echo "[d145] retiring postfix on 198 when this activation runs on the target host"
cd "$REPO_ROOT"
python3 -B -m tools.infra.retire_postfix_198 \
  --repo-root "$REPO_ROOT" \
  --ops-ledger "$OPS_LEDGER" \
  --execute

echo "[d145] rollback: systemctl enable --now postfix"
