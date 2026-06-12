#!/usr/bin/env bash
# scripts/quickstart.sh — one-command beta bring-up for STreasury bot.
#
# What it does:
#   1) prompts for the 5 required secrets/ids
#   2) runs deploy.sh --skip-backup
#   3) creates/updates DB role + schema on Brain
#   4) uploads /etc/streasury-bot/streasury.env
#   5) restarts service + health check + tail hints
#
# Usage:
#   SERVICES/streasury-bot/scripts/quickstart.sh
set -euo pipefail

SERVER_DEFAULT="162.0.208.88"
DB_HOST_DEFAULT="127.0.0.1"
DB_PORT_DEFAULT="25432"
DB_NAME_DEFAULT="appflowy"
SERVICE_ENV_PATH="/etc/streasury-bot/streasury.env"
SERVICE_NAME="streasury-bot"
SERVICE_PATH="/opt/streasury-bot"

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${HERE}/../../.." && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()   { echo -e "${GREEN}[quickstart]${NC} $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC} $*"; }
error() { echo -e "${RED}[error]${NC} $*"; }

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        error "missing required command: $1"
        exit 1
    fi
}

mask() {
    local s="$1"
    local n="${#s}"
    if (( n <= 8 )); then
        echo "********"
    else
        echo "${s:0:4}********${s:n-4:4}"
    fi
}

prompt() {
    local text="$1"
    local default="${2:-}"
    local value
    if [[ -n "$default" ]]; then
        read -r -p "$text [$default]: " value
        echo "${value:-$default}"
    else
        read -r -p "$text: " value
        echo "$value"
    fi
}

prompt_secret() {
    local text="$1"
    local value
    read -r -s -p "$text: " value
    echo ""
    echo "$value"
}

require_cmd ssh
require_cmd scp
require_cmd rsync
require_cmd python3

echo ""
log "STreasury beta quickstart (one command)"
echo ""

SERVER="$(prompt "Server IP / hostname" "$SERVER_DEFAULT")"
OWNER_TG_ID="$(prompt "Your Telegram numeric ID (from @userinfobot)")"
TELEGRAM_BOT_TOKEN="$(prompt_secret "New Telegram bot token (from @BotFather /revoke)")"
ANTHROPIC_API_KEY="$(prompt_secret "Anthropic API key")"
OPENAI_API_KEY="$(prompt_secret "OpenAI API key")"
DB_HOST="$(prompt "Database host (from server perspective)" "$DB_HOST_DEFAULT")"
DB_PORT="$(prompt "Database port" "$DB_PORT_DEFAULT")"
DB_NAME="$(prompt "Database name" "$DB_NAME_DEFAULT")"

DB_PASSWORD="$(prompt_secret "DB password for role 'streasury' (blank = auto-generate)")"
if [[ -z "$DB_PASSWORD" ]]; then
    if command -v openssl >/dev/null 2>&1; then
        DB_PASSWORD="$(openssl rand -base64 24 | tr -d '\n' | tr '/+' '_-')"
    else
        DB_PASSWORD="$(python3 - <<'PY'
import secrets, string
alphabet = string.ascii_letters + string.digits + "_-"
print("".join(secrets.choice(alphabet) for _ in range(32)))
PY
)"
    fi
    warn "Generated random DB password for role 'streasury'."
fi

DATABASE_URL="postgres://streasury:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

echo ""
log "Summary"
echo "  server:              $SERVER"
echo "  owner_tg_id:         $OWNER_TG_ID"
echo "  telegram token:      $(mask "$TELEGRAM_BOT_TOKEN")"
echo "  anthropic key:       $(mask "$ANTHROPIC_API_KEY")"
echo "  openai key:          $(mask "$OPENAI_API_KEY")"
echo "  database_url:        postgres://streasury:********@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo ""

read -r -p "Proceed? [y/N]: " PROCEED
if [[ "${PROCEED,,}" != "y" && "${PROCEED,,}" != "yes" ]]; then
    echo "Cancelled."
    exit 0
fi

log "Step 1/5: deploying service code"
STREASURY_TARGET_SERVER="$SERVER" "${ROOT}/SERVICES/streasury-bot/scripts/deploy.sh" --skip-backup

log "Step 2/5: creating/updating DB role + schema owner"
DB_PASSWORD_ESC="${DB_PASSWORD//\'/\'\'}"
ssh "root@${SERVER}" "sudo -u postgres psql -v ON_ERROR_STOP=1 -d ${DB_NAME} <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'streasury') THEN
        CREATE ROLE streasury LOGIN PASSWORD '${DB_PASSWORD_ESC}';
    ELSE
        ALTER ROLE streasury WITH PASSWORD '${DB_PASSWORD_ESC}';
    END IF;
END
\$\$;
GRANT CONNECT ON DATABASE ${DB_NAME} TO streasury;
CREATE SCHEMA IF NOT EXISTS streasury AUTHORIZATION streasury;
ALTER ROLE streasury IN DATABASE ${DB_NAME} SET search_path = streasury, public;
SQL"

log "Step 3/5: uploading env file"
TMP_ENV="$(mktemp)"
trap 'rm -f "$TMP_ENV"' EXIT
cat > "$TMP_ENV" <<EOF
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
OWNER_TG_ID=${OWNER_TG_ID}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
DATABASE_URL=${DATABASE_URL}
ANTHROPIC_MODEL=claude-sonnet-4-20250514
OPENAI_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o
OPENAI_WHISPER_MODEL=whisper-1
ASK_DEFAULT=claude
AUTO_CONFIRM=false
DEFAULT_CURRENCY=USD
COINGECKO_BASE=https://api.coingecko.com/api/v3
HTTP_HOST=0.0.0.0
HTTP_PORT=8620
LOG_LEVEL=INFO
DEFAULT_TENANT_ID=1
EOF

scp "$TMP_ENV" "root@${SERVER}:/tmp/streasury.env.$$"
ssh "root@${SERVER}" "install -d -m 0750 -o root -g streasury /etc/streasury-bot \
  && mv /tmp/streasury.env.$$ ${SERVICE_ENV_PATH} \
  && chown root:streasury ${SERVICE_ENV_PATH} \
  && chmod 0640 ${SERVICE_ENV_PATH}"

log "Step 4/5: applying schema + restarting service"
ssh "root@${SERVER}" "DB_URL=\$(grep '^DATABASE_URL=' ${SERVICE_ENV_PATH} | cut -d= -f2-) \
  && psql \"\$DB_URL\" -f ${SERVICE_PATH}/schema/streasury_schema.sql \
  && systemctl daemon-reload \
  && systemctl restart ${SERVICE_NAME}"

log "Step 5/5: health check"
HEALTH="$(ssh "root@${SERVER}" "curl -s -m 5 http://127.0.0.1:8620/health" || true)"
echo "  /health => ${HEALTH:-<empty>}"
if [[ "$HEALTH" == *'"ok":true'* || "$HEALTH" == *'"ok": true'* ]]; then
    log "✅ Service is healthy."
else
    warn "Health is not ok yet; showing latest logs:"
    ssh "root@${SERVER}" "journalctl -u ${SERVICE_NAME} -n 40 --no-pager" || true
fi

echo ""
log "Next in Telegram:"
echo "  /whoami"
echo "  /accounts add stripe USD revenue"
echo "  /log 100 revenue stripe \"quickstart test\""
echo "  /balance"
echo ""
log "DB password used for streasury role (save this safely):"
echo "  ${DB_PASSWORD}"
