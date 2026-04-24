#!/usr/bin/env bash
#
# Install sh-brain-index.service + sh-mcp-http.service on Secondary.
# Creates /opt/sh-brain/{index,mcp}/.venv, installs requirements, drops unit
# files, enables + starts them.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

[ "$EUID" -eq 0 ] || { echo "run as root"; exit 1; }

install -d /opt/sh-brain/index /opt/sh-brain/mcp /etc/sh-brain

# Sync code
rsync -a --delete "$ROOT/index/"  /opt/sh-brain/index/
rsync -a --delete "$ROOT/mcp/"    /opt/sh-brain/mcp/

# Venvs
for svc in index mcp; do
  if [ ! -d "/opt/sh-brain/$svc/.venv" ]; then
    python3 -m venv "/opt/sh-brain/$svc/.venv"
  fi
  /opt/sh-brain/$svc/.venv/bin/pip install -q --upgrade pip
  /opt/sh-brain/$svc/.venv/bin/pip install -q -r "/opt/sh-brain/$svc/requirements.txt"
done

# Env files for systemd
SECRETS=/root/sh-brain-secrets/brain.env
[ -f "$SECRETS" ] || { echo "missing $SECRETS"; exit 1; }
# shellcheck disable=SC1090
set -a; source "$SECRETS"; set +a

cat > /etc/sh-brain/index.env <<EOF
BRAIN_INDEX_DB_URL=postgres://brain_index:${BRAIN_INDEX_DB_PASSWORD}@127.0.0.1:5432/${POSTGRES_DB}
BRAIN_INDEX_TOKENS_FILE=/etc/sh-brain/index-tokens.json
BRAIN_INDEX_HOST=127.0.0.1
BRAIN_INDEX_PORT=28090
OLLAMA_BASE=${OLLAMA_BASE}
OLLAMA_EMBED_MODEL=${OLLAMA_EMBED_MODEL}
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_EMBED_MODEL=${OPENAI_EMBED_MODEL}
SH_APPFLOWY_BASE=http://127.0.0.1:28080
SH_MCP_USER=${SH_OWNER_EMAIL}
SH_MCP_PASSWORD=${SH_OWNER_PASSWORD}
SH_WORKSPACE_ID=${SH_WORKSPACE_ID:-}
EOF

cat > /etc/sh-brain/mcp-http.env <<EOF
SH_APPFLOWY_BASE=http://127.0.0.1:28080
SH_MCP_USER=${SH_OWNER_EMAIL}
SH_MCP_PASSWORD=${SH_OWNER_PASSWORD}
SH_WORKSPACE_ID=${SH_WORKSPACE_ID:-}
SH_INDEX_BASE=http://127.0.0.1:28090
SH_INDEX_TOKEN=SERVICE_INTERNAL_TOKEN
SH_MCP_TOKENS_FILE=/etc/sh-brain/mcp-tokens.json
SH_MCP_HTTP_HOST=127.0.0.1
SH_MCP_HTTP_PORT=28091
EOF

# Expose postgres on 127.0.0.1:5432 for brain-index? No — brain-index lives OUTSIDE docker.
# Map postgres to the host: update docker-compose to also publish 127.0.0.1:5432:5432.
# For simplicity, index service runs inside docker network via --network sh-brain_default.
# If you prefer host-networking, publish port 5432 on postgres service.

# Internal token the mcp uses to reach the index (written to both tokens files).
INTERNAL=$(openssl rand -hex 32)
if [ ! -f /etc/sh-brain/index-tokens.json ]; then
  echo "{\"$INTERNAL\":\"internal-mcp\"}" > /etc/sh-brain/index-tokens.json
  chmod 600 /etc/sh-brain/index-tokens.json
fi
if [ ! -f /etc/sh-brain/mcp-tokens.json ]; then
  echo "{}" > /etc/sh-brain/mcp-tokens.json
  chmod 600 /etc/sh-brain/mcp-tokens.json
fi
sed -i "s|SERVICE_INTERNAL_TOKEN|$INTERNAL|" /etc/sh-brain/mcp-http.env

# Unit files
install -m 644 "$ROOT/scripts/sh-brain-index.service" /etc/systemd/system/sh-brain-index.service
install -m 644 "$ROOT/scripts/sh-mcp-http.service"    /etc/systemd/system/sh-mcp-http.service

systemctl daemon-reload
systemctl enable --now sh-brain-index.service
systemctl enable --now sh-mcp-http.service

sleep 2
echo "— brain-index status —"
systemctl status --no-pager sh-brain-index.service | head -8
echo "— mcp-http status —"
systemctl status --no-pager sh-mcp-http.service    | head -8

echo
echo "Verify:"
echo "  curl -s http://127.0.0.1:28090/healthz | jq"
echo "  curl -s http://127.0.0.1:28091/healthz | jq"
echo "  curl -s https://brain.sunheart.com/mcp/healthz | jq"
