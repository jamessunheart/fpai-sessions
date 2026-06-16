#!/usr/bin/env bash
# d022 preference seed wrapper.
#
# Intended server install path:
#   /opt/fpai-build/scripts/seed_preference_pairs.sh
#
# Cron:
#   0 2 * * * /opt/fpai-build/scripts/seed_preference_pairs.sh

set -euo pipefail

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OUTPUT="${PREFERENCE_PAIRS_PATH:-/opt/fpai-build/data/preference_pairs.jsonl}"
OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}"

cd "$REPO_ROOT"

exec "$PYTHON_BIN" -B tools/learn/seed_preference_pairs.py \
  --output "$OUTPUT" \
  --ops-ledger "$OPS_LEDGER" \
  --require-proof
