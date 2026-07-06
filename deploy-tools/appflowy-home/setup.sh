#!/usr/bin/env bash
# Fill the AppFlowy-Cloud .env with strong secrets + your account + locked signups.
# Run from inside the cloned AppFlowy-Cloud dir (where .env lives).
# Usage: bash setup.sh <your-tailscale-fqdn> <your-email>
set -euo pipefail

FQDN="${1:?usage: setup.sh <tailscale-fqdn> <email>}"
EMAIL="${2:?usage: setup.sh <tailscale-fqdn> <email>}"
ENV=".env"
[ -f "$ENV" ] || { echo "no .env here — run from the AppFlowy-Cloud clone (cp deploy.env .env first)"; exit 1; }

gen() { openssl rand -hex 32; }
setk() { # setk KEY VALUE  — replace or append in .env
  local k="$1" v="$2"
  if grep -qE "^${k}=" "$ENV"; then
    # escape & for sed
    v_esc=$(printf '%s' "$v" | sed 's/[&/\]/\\&/g')
    sed -i "s/^${k}=.*/${k}=${v_esc}/" "$ENV"
  else
    printf '%s=%s\n' "$k" "$v" >> "$ENV"
  fi
}

echo "== generating secrets =="
setk FQDN "$FQDN"
setk SCHEME "https"
setk WS_SCHEME "wss"
setk GOTRUE_JWT_SECRET "$(gen)"
setk APPFLOWY_GOTRUE_JWT_SECRET "$(gen)"
setk GOTRUE_ADMIN_EMAIL "$EMAIL"
setk GOTRUE_ADMIN_PASSWORD "$(gen | cut -c1-24)"
setk POSTGRES_PASSWORD "$(gen)"
setk APPFLOWY_S3_SECRET_KEY "$(gen)"
setk APPFLOWY_S3_ACCESS_KEY "$(gen | cut -c1-20)"
setk APPFLOWY_REDIS_URI "redis://redis:6379"

echo "== lock signups to just you (after first login) =="
setk GOTRUE_DISABLE_SIGNUP "false"   # keep false until you sign up once, then flip to true
setk GOTRUE_MAILER_AUTOCONFIRM "true"  # no SMTP needed for a solo brain

echo
echo "DONE. Next:"
echo "  1) docker compose up -d"
echo "  2) open the app -> Self-hosted Cloud -> https://$FQDN -> sign up as $EMAIL"
echo "  3) then set GOTRUE_DISABLE_SIGNUP=true in .env and: docker compose up -d gotrue"
echo "  admin password (save it) is in .env: GOTRUE_ADMIN_PASSWORD"
