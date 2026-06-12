#!/usr/bin/env bash
# Deploy chief-of-staff to brain server (162.0.208.88).
# Mirrors streasury-bot's deploy pattern: rsync source + state snapshot,
# remote bootstrap, restart, health check.
set -euo pipefail

SERVER="${COS_TARGET_SERVER:-162.0.208.88}"
SERVICE_NAME="chief-of-staff"
SERVICE_PORT="8107"
DEPLOY_PATH="/opt/chief-of-staff"

HERE="$(cd "$(dirname "$0")" && pwd)"
LOCAL_PATH="$(cd "${HERE}/.." && pwd)"
COCKPIT_ROOT="$(cd "${LOCAL_PATH}/../.." && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $*"; }
err()  { echo -e "${RED}[err]${NC}   $*"; }

# 1) syntax
log "Step 1/6: local Python syntax check"
SYNTAX_FAIL=0
for pyfile in $(find "${LOCAL_PATH}/app" -name '*.py' -type f); do
    if ! python3 -m py_compile "${pyfile}" 2>/dev/null; then
        err "syntax error: ${pyfile}"
        SYNTAX_FAIL=1
    fi
done
[[ "${SYNTAX_FAIL}" -ne 0 ]] && { err "fix syntax first"; exit 1; }
log "✅ syntax OK"

# 2a) refresh priority snapshot from current SERVICES/
log "Step 2a/6: refresh priority snapshot from local SERVICES/"
( cd "${LOCAL_PATH}" && python3 -c "from app.catalog import dump_snapshot; print(dump_snapshot())" )
log "✅ snapshot written to core/STATE/priority_snapshot.json"

# 2b) refresh ZV revenue counts (best-effort — won't fail deploy)
log "Step 2b/6: refresh ZV revenue counts"
bash "${HERE}/refresh_revenue.sh" || warn "ZV revenue refresh skipped"

# 2c) refresh Outbounders revenue (best-effort)
log "Step 2c/6: refresh Outbounders revenue"
bash "${HERE}/refresh_outbounders.sh" || warn "Outbounders revenue refresh skipped"

# 3) rsync source
log "Step 3/6: rsync source → root@${SERVER}:${DEPLOY_PATH}/"
ssh "root@${SERVER}" "mkdir -p '${DEPLOY_PATH}'"
rsync -avz --delete \
    --exclude '__pycache__' --exclude '*.pyc' --exclude '.venv' \
    --exclude '.env' --exclude '.git' --exclude '*.log' --exclude 'tests' \
    "${LOCAL_PATH}/" "root@${SERVER}:${DEPLOY_PATH}/" >/dev/null
log "✅ source synced"

# 4) ship state files (catalog/ledger/snapshot) into deploy dir as state/
log "Step 4/6: rsync state files → ${DEPLOY_PATH}/state/"
ssh "root@${SERVER}" "mkdir -p '${DEPLOY_PATH}/state'"
rsync -avz \
    "${COCKPIT_ROOT}/core/STATE/catalog.json" \
    "${COCKPIT_ROOT}/core/STATE/ledger.json" \
    "${COCKPIT_ROOT}/core/STATE/priority_snapshot.json" \
    "root@${SERVER}:${DEPLOY_PATH}/state/" >/dev/null
log "✅ state files synced"

# 5) bootstrap + restart
log "Step 5/6: remote bootstrap + restart"
ssh "root@${SERVER}" "bash '${DEPLOY_PATH}/scripts/bootstrap.sh'"
ssh "root@${SERVER}" "systemctl daemon-reload && systemctl restart ${SERVICE_NAME}"
sleep 3

if ssh "root@${SERVER}" "systemctl is-active --quiet ${SERVICE_NAME}"; then
    log "✅ unit active"
else
    err "service failed. Last 30 log lines:"
    ssh "root@${SERVER}" "journalctl -u ${SERVICE_NAME} -n 30 --no-pager"
    exit 1
fi

# 6) health check
log "Step 6/6: health check"
HEALTH=$(ssh "root@${SERVER}" "curl -s -m 5 http://127.0.0.1:${SERVICE_PORT}/health" 2>/dev/null || echo '')
if echo "${HEALTH}" | grep -q '"status".*"healthy"'; then
    log "✅ /health says healthy"
else
    warn "health endpoint returned: ${HEALTH:-<empty>}"
fi

MONEY=$(ssh "root@${SERVER}" "curl -s -m 5 http://127.0.0.1:${SERVICE_PORT}/money" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'cost=\${d[\"total_cost_monthly_usd\"]} leak={d[\"biggest_leak\"][\"name\"] if d.get(\"biggest_leak\") else None}')")
log "money snapshot: ${MONEY}"

PRIORITY=$(ssh "root@${SERVER}" "curl -s -m 5 http://127.0.0.1:${SERVICE_PORT}/priority" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'services={d[\"total_services\"]} by_role={d[\"by_role\"]}')")
log "priority snapshot: ${PRIORITY}"

echo ""
echo "  service:   ${SERVICE_NAME}"
echo "  server:    ${SERVER}"
echo "  port:      ${SERVICE_PORT} (loopback only)"
echo "  path:      ${DEPLOY_PATH}"
echo "  env:       /etc/chief-of-staff/chief.env"
echo ""
echo "  next:      ssh root@${SERVER} 'journalctl -u ${SERVICE_NAME} -f'"
echo ""
log "🎉 done"
