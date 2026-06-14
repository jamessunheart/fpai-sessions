#!/usr/bin/env bash
# Pull /opt/chief-of-staff/state/ledger.json from the brain server back to the
# repo, so /money edits made via @sunheartbrain_bot land in core/STATE/ledger.json
# and can be committed.
#
# The brain ledger is the live SoT (chief-of-staff reads from it directly).
# The repo copy is a snapshot — stays in sync via this pull + git commit.
#
# Usage: ./sync_ledger_from_brain.sh
set -euo pipefail

REPO_LEDGER="${REPO_LEDGER:-/Users/jamessunheart/FPAI_Cockpit/core/STATE/ledger.json}"
BRAIN_HOST="${BRAIN_HOST:-root@162.0.208.88}"
BRAIN_LEDGER="${BRAIN_LEDGER:-/opt/chief-of-staff/state/ledger.json}"

scp -o ConnectTimeout=5 "${BRAIN_HOST}:${BRAIN_LEDGER}" "${REPO_LEDGER}"
echo "synced ${BRAIN_HOST}:${BRAIN_LEDGER} → ${REPO_LEDGER}"
echo ""
echo "now: cd \$(dirname \"${REPO_LEDGER}\")/.. && git diff core/STATE/ledger.json"
echo "     git add core/STATE/ledger.json && git commit -m 'sync(money): pull bot edits from brain'"
