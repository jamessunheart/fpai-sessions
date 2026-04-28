#!/usr/bin/env bash
# scripts/deploy.sh — wrapper that respects AGENTS.md (no direct SSH).
#
# Forwards to infra/scripts/deploy-to-server.sh with the right service name
# and target host. The deploy-to-server.sh script handles backup, rsync,
# venv build, schema apply, systemctl restart, and health check.
set -euo pipefail

SERVICE_NAME="streasury-bot"
TARGET_HOST="${TARGET_HOST:-brain}"   # brain == 162.0.208.88

# Locate the FPAI cockpit root (this script lives at SERVICES/<name>/scripts/)
HERE="$(cd "$(dirname "$0")" && pwd)"
COCKPIT_ROOT="$(cd "${HERE}/../../.." && pwd)"

cd "${COCKPIT_ROOT}"

if [[ ! -x "infra/scripts/deploy-to-server.sh" ]]; then
    echo "Error: infra/scripts/deploy-to-server.sh not found or not executable." >&2
    echo "AGENTS.md mandates we route deploys through it. Aborting." >&2
    exit 1
fi

echo "[deploy] ${SERVICE_NAME} → ${TARGET_HOST}"
exec infra/scripts/deploy-to-server.sh "${SERVICE_NAME}" "${TARGET_HOST}"
