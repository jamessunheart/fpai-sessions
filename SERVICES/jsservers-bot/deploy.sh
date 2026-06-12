#!/bin/bash
# Deploy jsservers-bot to primary server.
#
# Usage:
#   ./deploy.sh                       # uses BOT_TOKEN from local env (or prompts), DISCOVER whitelist
#   ./deploy.sh --user-ids 123,456    # locks whitelist to given Telegram user IDs
#   BOT_TOKEN=xxx ./deploy.sh --user-ids 123
#
# Idempotent: re-run any time to update code, env, or whitelist.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_IP="198.54.123.234"
SERVER_USER="root"
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)
REMOTE="${SERVER_USER}@${SERVER_IP}"
REMOTE_DIR="/opt/fpai/jsservers-bot"
ENV_FILE="/root/.jsservers-bot.env"
SERVICE="jsservers-bot"

USER_IDS="DISCOVER"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --user-ids) USER_IDS="$2"; shift 2 ;;
        --token)    BOT_TOKEN="$2";  shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "${BOT_TOKEN:-}" ]]; then
    echo "BOT_TOKEN not provided. Set env var or pass --token <token>." >&2
    exit 2
fi

if [[ ! -f "$SSH_KEY" ]]; then
    echo "SSH key not found: $SSH_KEY" >&2
    exit 2
fi

echo "==> Verifying server reachability"
ssh "${SSH_OPTS[@]}" "$REMOTE" 'echo connected; uname -a'

echo "==> Ensuring remote dir exists"
ssh "${SSH_OPTS[@]}" "$REMOTE" "mkdir -p ${REMOTE_DIR}"

echo "==> Syncing code"
rsync -az --delete \
    -e "ssh ${SSH_OPTS[*]}" \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude 'deploy.sh' \
    --exclude 'README.md' \
    "$SCRIPT_DIR/" "$REMOTE:$REMOTE_DIR/"

echo "==> Writing env file (mode 600)"
ssh "${SSH_OPTS[@]}" "$REMOTE" "umask 077 && cat > $ENV_FILE" <<EOF
BOT_TOKEN=$BOT_TOKEN
ALLOWED_USER_IDS=$USER_IDS
EOF
ssh "${SSH_OPTS[@]}" "$REMOTE" "chmod 600 $ENV_FILE"

echo "==> Setting up venv + dependencies"
ssh "${SSH_OPTS[@]}" "$REMOTE" "
    set -e
    cd $REMOTE_DIR
    if [ ! -d .venv ]; then
        python3 -m venv .venv
    fi
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -r requirements.txt
"

echo "==> Installing systemd unit"
ssh "${SSH_OPTS[@]}" "$REMOTE" "
    cp $REMOTE_DIR/jsservers-bot.service /etc/systemd/system/${SERVICE}.service
    systemctl daemon-reload
    systemctl enable ${SERVICE}
    systemctl restart ${SERVICE}
"

echo "==> Waiting 4s for startup"
sleep 4

echo "==> Status"
ssh "${SSH_OPTS[@]}" "$REMOTE" "systemctl is-active ${SERVICE} && systemctl status ${SERVICE} --no-pager -n 5"

echo "==> Recent logs"
ssh "${SSH_OPTS[@]}" "$REMOTE" "journalctl -u ${SERVICE} -n 20 --no-pager"

echo
echo "✅ Deploy complete."
echo "   Whitelist: $USER_IDS"
if [[ "$USER_IDS" == "DISCOVER" ]]; then
    echo "   ⚠️  Bot is in DISCOVER mode — anyone can use it. Lock it ASAP:"
    echo "      ./deploy.sh --user-ids <YOUR_TELEGRAM_USER_ID>"
fi
echo "   Tail logs: ssh -i $SSH_KEY $REMOTE 'journalctl -u $SERVICE -f'"
