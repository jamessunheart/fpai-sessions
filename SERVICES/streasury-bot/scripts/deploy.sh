#!/usr/bin/env bash
# scripts/deploy.sh — deploy streasury-bot to Brain (162.0.208.88).
#
# Follows the FPAI deploy pattern (rsync + remote bootstrap + systemd) with
# pre-deploy backup, syntax check, and post-deploy health check. Per AGENTS.md,
# the only canonical deploy path for this repo runs as root over ssh.
#
# Usage:
#   scripts/deploy.sh                # standard deploy
#   scripts/deploy.sh --skip-backup  # if /opt/fpai/backups isn't yet set up
#   scripts/deploy.sh --dry-run      # show what would happen, do nothing
set -euo pipefail

SERVER="${STREASURY_TARGET_SERVER:-162.0.208.88}"
SERVICE_NAME="streasury-bot"
SERVICE_PORT="8620"
DEPLOY_PATH="/opt/streasury-bot"
ENV_DIR="/etc/streasury-bot"
BACKUP_DIR="/opt/fpai/backups/streasury-bot"

HERE="$(cd "$(dirname "$0")" && pwd)"
LOCAL_PATH="$(cd "${HERE}/.." && pwd)"

SKIP_BACKUP=false
DRY_RUN=false
for arg in "$@"; do
    case "${arg}" in
        --skip-backup) SKIP_BACKUP=true ;;
        --dry-run)     DRY_RUN=true ;;
        --help|-h)
            grep '^#' "$0" | head -25
            exit 0
            ;;
    esac
done

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()   { echo -e "${GREEN}[deploy]${NC} $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }
err()   { echo -e "${RED}[err]${NC}   $*"; }

run_remote() {
    if [[ "${DRY_RUN}" == true ]]; then
        echo "  ssh root@${SERVER} \"$*\""
    else
        ssh "root@${SERVER}" "$@"
    fi
}

run_local() {
    if [[ "${DRY_RUN}" == true ]]; then
        echo "  $*"
    else
        eval "$*"
    fi
}

# ─── Step 1: local syntax check ──────────────────────────────────────────────
log "Step 1/6: local Python syntax check"
SYNTAX_FAIL=0
for pyfile in $(find "${LOCAL_PATH}/app" -name '*.py' -type f); do
    if ! python3 -m py_compile "${pyfile}" 2>/dev/null; then
        err "syntax error: ${pyfile}"
        SYNTAX_FAIL=1
    fi
done
if [[ "${SYNTAX_FAIL}" -ne 0 ]]; then
    err "fix syntax errors before deploying"
    exit 1
fi
log "✅ syntax OK"

# ─── Step 2: pre-deploy backup ───────────────────────────────────────────────
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
if [[ "${SKIP_BACKUP}" == false ]]; then
    log "Step 2/6: pre-deploy backup → ${BACKUP_DIR}/${TIMESTAMP}"
    run_remote "mkdir -p '${BACKUP_DIR}'"
    if run_remote "test -d '${DEPLOY_PATH}'" 2>/dev/null; then
        run_remote "rsync -a --exclude '__pycache__' --exclude '.venv' \
                          '${DEPLOY_PATH}/' '${BACKUP_DIR}/${TIMESTAMP}/'"
        log "✅ source backed up"
    else
        warn "no existing deploy at ${DEPLOY_PATH} — first install"
    fi
    if run_remote "test -f '${ENV_DIR}/streasury.env'"; then
        run_remote "psql -At -U postgres -d appflowy -c \
            \"SELECT COUNT(*) FROM streasury.txn\" >/dev/null 2>&1 \
            && pg_dump --schema=streasury --no-owner --dbname=\"\$(grep ^DATABASE_URL ${ENV_DIR}/streasury.env | cut -d= -f2-)\" \
               | gzip > '${BACKUP_DIR}/${TIMESTAMP}-schema.sql.gz' \
            || echo 'schema not yet populated, skipping pg_dump'"
        log "✅ schema dump attempted"
    else
        warn "no env file yet — skipping pg_dump"
    fi
else
    warn "Step 2/6: --skip-backup specified, skipping"
fi

# ─── Step 3: rsync source ────────────────────────────────────────────────────
log "Step 3/6: rsync source → root@${SERVER}:${DEPLOY_PATH}/"
run_remote "mkdir -p '${DEPLOY_PATH}'"
RSYNC_CMD="rsync -avz --delete \
    --exclude '__pycache__' --exclude '*.pyc' --exclude '.venv' \
    --exclude '.env' --exclude '.git' \
    '${LOCAL_PATH}/' 'root@${SERVER}:${DEPLOY_PATH}/'"
run_local "${RSYNC_CMD}"
log "✅ source synced"

# ─── Step 4: remote bootstrap (idempotent) ──────────────────────────────────
log "Step 4/6: remote bootstrap (venv + schema + systemd)"
run_remote "bash '${DEPLOY_PATH}/scripts/bootstrap.sh'"
log "✅ bootstrap done"

# ─── Step 5: restart + health ────────────────────────────────────────────────
log "Step 5/6: restart + health check"
run_remote "systemctl daemon-reload && systemctl restart ${SERVICE_NAME}"
sleep 6

if run_remote "systemctl is-active --quiet ${SERVICE_NAME}"; then
    log "✅ unit active"
else
    err "service failed to start. Last 30 log lines:"
    run_remote "journalctl -u ${SERVICE_NAME} -n 30 --no-pager"
    err "check that ${ENV_DIR}/streasury.env has real values for TELEGRAM_BOT_TOKEN, OWNER_TG_ID, ANTHROPIC_API_KEY, OPENAI_API_KEY, DATABASE_URL"
    exit 1
fi

HEALTH=$(run_remote "curl -s -m 5 http://127.0.0.1:${SERVICE_PORT}/health" 2>/dev/null || echo '')
if echo "${HEALTH}" | grep -q '"ok": *true'; then
    log "✅ /health says ok"
else
    warn "health endpoint returned: ${HEALTH:-<empty>}"
    warn "(if this is the first deploy and the env file is empty, populate ${ENV_DIR}/streasury.env then re-run)"
fi

# ─── Step 6: summary ─────────────────────────────────────────────────────────
log "Step 6/6: summary"
echo ""
echo "  service:   ${SERVICE_NAME}"
echo "  server:    ${SERVER}"
echo "  port:      ${SERVICE_PORT}"
echo "  path:      ${DEPLOY_PATH}"
echo "  env:       ${ENV_DIR}/streasury.env"
echo "  backup:    ${BACKUP_DIR}/${TIMESTAMP}"
echo ""
echo "  next:      ssh root@${SERVER} 'journalctl -u ${SERVICE_NAME} -f'"
echo "             open Telegram → @STreasury_Bot → /whoami"
echo ""
log "🎉 done"
