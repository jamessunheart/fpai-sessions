#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}"

echo "[d146] auditing cruft services on 198; live stop requires FPAI_D146_CRUFT_STOP=1"
cd "$REPO_ROOT"
python3 -B -m tools.infra.stop_cruft_services_198 \
  --repo-root "$REPO_ROOT" \
  --ops-ledger "$OPS_LEDGER" \
  --execute \
  --record

echo "[d146] rollback: systemctl enable --now fpai-cocoon.service whaletrack-magnet.service"
