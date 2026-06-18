#!/usr/bin/env bash
# Prepare/run Postiz self-hosting artifacts on server 162 after merge.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
POSTIZ_ROOT="${POSTIZ_ROOT:-/opt/postiz-docker-compose}"
POSTIZ_COMPOSE_REPO="${POSTIZ_COMPOSE_REPO:-https://github.com/gitroomhq/postiz-docker-compose}"
POSTIZ_PUBLIC_URL="${POSTIZ_PUBLIC_URL:-https://postiz.fullpotential.ai}"
POSTIZ_ENV="${POSTIZ_ENV:-/etc/fpai/postiz.env}"
MCP_OUT_DIR="${MCP_OUT_DIR:-/etc/fpai/mcp}"

echo "[d099] Postiz social scheduler activation"
echo "[d099] root: $POSTIZ_ROOT"
echo "[d099] public URL: $POSTIZ_PUBLIC_URL"

if [[ "${POSTIZ_ACTIVATE:-0}" != "1" ]]; then
  echo "[d099] dry-run only. Set POSTIZ_ACTIVATE=1 after merge to clone/update Postiz compose."
  echo "[d099] live start remains gated by POSTIZ_START=1."
  exit 0
fi

command -v git >/dev/null 2>&1 || { echo "[d099] git is required" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "[d099] docker is required" >&2; exit 1; }

if [[ -d "$POSTIZ_ROOT/.git" ]]; then
  git -C "$POSTIZ_ROOT" pull --ff-only
else
  git clone "$POSTIZ_COMPOSE_REPO" "$POSTIZ_ROOT"
fi

install -d -m 0755 "$(dirname "$POSTIZ_ENV")" "$MCP_OUT_DIR"

if [[ ! -f "$POSTIZ_ENV" ]]; then
  umask 077
  cat >"$POSTIZ_ENV" <<EOF
# d099 Postiz live env.
# Fill this from Postiz docs and live secrets; do not commit this file.
POSTIZ_PUBLIC_URL=$POSTIZ_PUBLIC_URL
NEXT_PUBLIC_BACKEND_URL=$POSTIZ_PUBLIC_URL
EOF
  echo "[d099] wrote env template at $POSTIZ_ENV; fill required secrets/settings before POSTIZ_START=1" >&2
fi

(
  cd "$REPO"
  python3 -m tools.postiz.wire mcp-config \
    --base-url "$POSTIZ_PUBLIC_URL" \
    --api-key-ref '${POSTIZ_API_KEY}' \
    --output "$MCP_OUT_DIR/postiz.mcp.json"
)
chmod 0600 "$MCP_OUT_DIR/postiz.mcp.json"
echo "[d099] wrote MCP fragment: $MCP_OUT_DIR/postiz.mcp.json"

if [[ "${POSTIZ_START:-0}" != "1" ]]; then
  echo "[d099] compose checkout/config fragment ready. Set POSTIZ_START=1 to run docker compose up -d."
  exit 0
fi

if [[ "${POSTIZ_ENV_READY:-0}" != "1" ]]; then
  echo "[d099] refusing to start until POSTIZ_ENV_READY=1 confirms $POSTIZ_ENV was reviewed" >&2
  exit 1
fi

(
  cd "$POSTIZ_ROOT"
  docker compose --env-file "$POSTIZ_ENV" pull
  docker compose --env-file "$POSTIZ_ENV" up -d
  docker compose ps
)

echo "[d099] Postiz started. Next proof: create/connect Mastodon, generate Postiz API key, install MCP fragment in Ember config, then call integrationList and schedulePostTool."
