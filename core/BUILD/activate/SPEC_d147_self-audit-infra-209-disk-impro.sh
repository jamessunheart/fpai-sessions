#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}"
STATE_DIR="${FPAI_D147_STATE_DIR:-/opt/fpai-build/state}"
REPORT_DIR="${FPAI_D147_REPORT_DIR:-/opt/fpai-build/reports}"

cd "$REPO_ROOT"

python3 -B -m tools.infra.report_disk_growth_209 \
  --repo-root "$REPO_ROOT" \
  --previous-snapshot "$STATE_DIR/d147_disk_209_snapshot.json" \
  --snapshot-out "$STATE_DIR/d147_disk_209_snapshot.json" \
  --report-json "$REPORT_DIR/d147_disk_209_report.json" \
  --report-md "$REPORT_DIR/d147_disk_209_report.md" \
  --ops-ledger "$OPS_LEDGER" \
  --record
