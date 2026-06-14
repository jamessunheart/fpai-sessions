#!/usr/bin/env bash
#
# Sunheart Brain — first-time bootstrap.
# Run this on Secondary (162.0.208.88) as root AFTER:
#   1. brain.sunheart.com A record → 162.0.208.88 has propagated
#   2. This repo has been rsync'd to /opt/sh-brain
#
# Steps (each idempotent):
#   1. Create /root/sh-brain-secrets with strong random creds (or keep existing)
#   2. Bring up the docker stack (postgres + gotrue + minio + appflowy_cloud + admin_frontend + appflowy_web + internal nginx)
#   3. Wait for health, create the brain_index DB role + grant
#   4. Drop nginx vhost into /etc/nginx/sites-*
#   5. Issue Let's Encrypt cert via dockerized certbot
#   6. Reload nginx
#
# After this exits successfully, run:
#   ./provision_user.sh              # create owner, grab workspace_id
#   python3 ../schema/build_schema.py  --purge-defaults
#   ./install_systemd.sh
#   ./issue_token.sh <agent_name>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SECRETS_DIR=/root/sh-brain-secrets
ENV_FILE="$SECRETS_DIR/brain.env"
ETC_DIR=/etc/sh-brain
WEB_DOMAIN=brain.sunheart.com
COMPOSE_PROJECT=sh-brain

C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_RED='\033[0;31m'; C_NC='\033[0m'
log()  { echo -e "${C_GREEN}[sh-brain]${C_NC} $*"; }
warn() { echo -e "${C_YELLOW}[sh-brain]${C_NC} $*"; }
die()  { echo -e "${C_RED}[sh-brain]${C_NC} $*" >&2; exit 1; }

[ "$EUID" -eq 0 ] || die "run as root"
command -v docker >/dev/null  || die "docker missing"
command -v docker compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1 || die "docker compose plugin missing"

# ---------------------------------------------------------------------------
# 1. Secrets
# ---------------------------------------------------------------------------

mkdir -p "$SECRETS_DIR" "$ETC_DIR"
chmod 700 "$SECRETS_DIR" "$ETC_DIR"

if [ ! -f "$ENV_FILE" ]; then
  log "generating $ENV_FILE"
  POSTGRES_PW=$(openssl rand -hex 32)
  MINIO_AK="shbrain$(openssl rand -hex 6)"
  MINIO_SK=$(openssl rand -hex 24)
  JWT=$(openssl rand -hex 32)
  ADMIN_PW=$(openssl rand -base64 24)
  OWNER_PW=$(openssl rand -base64 24)
  BRAIN_INDEX_PW=$(openssl rand -hex 32)

  cat > "$ENV_FILE" <<EOF
# ========== URLs ==========
APPFLOWY_BASE_URL=https://$WEB_DOMAIN
APPFLOWY_WEB_URL=https://$WEB_DOMAIN
APPFLOWY_WEBSOCKET_BASE_URL=wss://$WEB_DOMAIN/ws
API_EXTERNAL_URL=https://$WEB_DOMAIN/gotrue

# ========== Postgres ==========
POSTGRES_HOST=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$POSTGRES_PW
POSTGRES_DB=postgres
POSTGRES_PORT=5432
APPFLOWY_DATABASE_URL=postgres://postgres:$POSTGRES_PW@postgres:5432/postgres
GOTRUE_DATABASE_URL=postgres://postgres:$POSTGRES_PW@postgres:5432/postgres?search_path=auth
APPFLOWY_DATABASE_MAX_CONNECTIONS=40

# brain-index connects as its own role, set by bootstrap's ALTER ROLE step
BRAIN_INDEX_DB_PASSWORD=$BRAIN_INDEX_PW
BRAIN_INDEX_DB_URL=postgres://brain_index:$BRAIN_INDEX_PW@127.0.0.1:25432/postgres

# ========== Redis ==========
APPFLOWY_REDIS_URI=redis://redis:6379

# ========== MinIO (S3) ==========
APPFLOWY_S3_ACCESS_KEY=$MINIO_AK
APPFLOWY_S3_SECRET_KEY=$MINIO_SK
APPFLOWY_S3_BUCKET=appflowy
APPFLOWY_S3_USE_MINIO=true
APPFLOWY_S3_MINIO_URL=http://minio:9000
APPFLOWY_S3_CREATE_BUCKET=true
APPFLOWY_S3_REGION=

# ========== GoTrue ==========
GOTRUE_JWT_SECRET=$JWT
GOTRUE_JWT_EXP=7200
GOTRUE_ADMIN_EMAIL=admin@sunheart.com
GOTRUE_ADMIN_PASSWORD=$ADMIN_PW
GOTRUE_DISABLE_SIGNUP=false
GOTRUE_MAILER_AUTOCONFIRM=true

# SMTP (optional — leave blank until you paste in a Resend key)
GOTRUE_SMTP_HOST=
GOTRUE_SMTP_PORT=465
GOTRUE_SMTP_USER=
GOTRUE_SMTP_PASS=
GOTRUE_SMTP_ADMIN_EMAIL=admin@sunheart.com

# ========== Workspace owner (provisioned by scripts/provision_user.sh) ==========
SH_OWNER_EMAIL=james.rick.stinson@gmail.com
SH_OWNER_PASSWORD=$OWNER_PW

# ========== Embeddings / AI ==========
OLLAMA_BASE=http://host.docker.internal:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OPENAI_API_KEY=
OPENAI_EMBED_MODEL=text-embedding-3-small
AI_OPENAI_API_KEY=

RUST_LOG=info
EOF
  chmod 600 "$ENV_FILE"
else
  log "reusing existing $ENV_FILE"
fi

# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

# ---------------------------------------------------------------------------
# 2. Compose up
# ---------------------------------------------------------------------------

log "bringing up docker stack (project=$COMPOSE_PROJECT)"
install -d /opt/sh-brain
rsync -a --delete "$ROOT/compose/" /opt/sh-brain/compose/
docker compose -p "$COMPOSE_PROJECT" --env-file "$ENV_FILE" -f /opt/sh-brain/compose/docker-compose.yml up -d

log "waiting for postgres healthy (up to 60s)"
for _ in $(seq 1 30); do
  if docker exec sh-brain-postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# ---------------------------------------------------------------------------
# 3. brain_index DB role password
# ---------------------------------------------------------------------------

log "configuring brain_index DB role password"
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" sh-brain-postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "ALTER ROLE brain_index WITH PASSWORD '$BRAIN_INDEX_DB_PASSWORD';" >/dev/null

# ---------------------------------------------------------------------------
# 4. Host nginx vhost (two-phase: HTTP-only → issue cert → install full vhost)
# ---------------------------------------------------------------------------

if command -v nginx >/dev/null; then
  install -d -m 755 /var/www/letsencrypt

  HAS_CERT=0
  [ -f "/etc/letsencrypt/live/$WEB_DOMAIN/fullchain.pem" ] && HAS_CERT=1

  if [ "$HAS_CERT" -eq 0 ]; then
    log "phase 4a: installing HTTP-only vhost so certbot can solve ACME"
    cat > /etc/nginx/sites-available/brain.sunheart.com.conf <<EOF_HTTP
server {
    listen 80;
    listen [::]:80;
    server_name $WEB_DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/letsencrypt; }
    location / { return 200 "sh-brain: waiting for TLS\n"; add_header Content-Type text/plain; }
}
EOF_HTTP
    [ -L /etc/nginx/sites-enabled/brain.sunheart.com.conf ] || \
      ln -s ../sites-available/brain.sunheart.com.conf /etc/nginx/sites-enabled/brain.sunheart.com.conf
    nginx -t && systemctl reload nginx

    log "phase 4b: issuing Let's Encrypt cert via dockerized certbot (avoids host pyOpenSSL mismatches)"
    docker run --rm \
      -v /etc/letsencrypt:/etc/letsencrypt \
      -v /var/lib/letsencrypt:/var/lib/letsencrypt \
      -v /var/www/letsencrypt:/var/www/letsencrypt \
      certbot/certbot certonly --webroot -w /var/www/letsencrypt \
      -d "$WEB_DOMAIN" --non-interactive --agree-tos -m "admin@sunheart.com" || \
      die "certbot (docker) failed — check DNS + /var/log/letsencrypt"
  else
    log "cert already exists for $WEB_DOMAIN"
  fi

  log "phase 4c: installing full HTTPS vhost"
  install -m 644 "$ROOT/nginx/brain.sunheart.com.conf" /etc/nginx/sites-available/brain.sunheart.com.conf
  [ -L /etc/nginx/sites-enabled/brain.sunheart.com.conf ] || \
    ln -s ../sites-available/brain.sunheart.com.conf /etc/nginx/sites-enabled/brain.sunheart.com.conf

  if nginx -t; then
    systemctl reload nginx
  else
    die "nginx -t failed after installing full vhost — investigate"
  fi
else
  warn "nginx not installed on host — skipping vhost step"
fi

log "bootstrap done. Next:"
echo "  $ROOT/scripts/provision_user.sh"
echo "  python3 $ROOT/schema/build_schema.py --purge-defaults"
echo "  $ROOT/scripts/install_systemd.sh"
echo "  $ROOT/scripts/issue_token.sh sunheart"
