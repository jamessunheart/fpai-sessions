#!/usr/bin/env bash
# Re-deploy the zenvillage.live/peace static site to primary FPAI server.
# Usage:  ./deploy.sh [--with-nginx]
#
# By default this only syncs the page files. The nginx vhost is managed by
# certbot on the server (it owns the SSL block), so we do NOT overwrite it
# unless you explicitly pass --with-nginx (and you'll need to re-run certbot
# afterward to restore SSL).
#
# Idempotent. Safe to run any time after editing peace/index.html.

set -euo pipefail

SERVER_IP="198.54.123.234"
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"
DEPLOY_PATH="/var/www/zenvillage-live"

WITH_NGINX="false"
if [[ "${1:-}" == "--with-nginx" ]]; then WITH_NGINX="true"; fi

cd "$(dirname "$0")"

echo "→ rsync site files"
# NOTE: peace/ has server-only subdirs (thanks/, menu/) that are NOT in this
# repo. Do NOT use --delete on peace/ or you will nuke them. (Learned the hard
# way 2026-07-10.) Only sync files that exist locally; skip absent dirs so a
# stale checkout doesn't abort the whole deploy under `set -e`.
rsync -avz -e "ssh $SSH_OPTS" peace/ "root@${SERVER_IP}:${DEPLOY_PATH}/peace/"
[[ -d manage ]] && rsync -avz -e "ssh $SSH_OPTS" manage/ "root@${SERVER_IP}:${DEPLOY_PATH}/manage/" || echo "  (skip manage/ — not in this checkout)"
[[ -d buy ]]    && rsync -avz -e "ssh $SSH_OPTS" buy/    "root@${SERVER_IP}:${DEPLOY_PATH}/buy/"    || echo "  (skip buy/ — not in this checkout)"
# 5 Day Reset Retreat landing + invite-only affiliate signup (live 2026-05-17)
[[ -d reset ]]  && rsync -avz -e "ssh $SSH_OPTS" reset/  "root@${SERVER_IP}:${DEPLOY_PATH}/reset/"  || echo "  (skip reset/ — not in this checkout)"

if [[ "$WITH_NGINX" == "true" ]]; then
  echo "⚠  --with-nginx: pushing nginx vhost (will overwrite SSL config)"
  scp $SSH_OPTS nginx/zenvillage.live.conf "root@${SERVER_IP}:/etc/nginx/sites-available/zenvillage.live.conf"
  ssh $SSH_OPTS "root@${SERVER_IP}" '
    ln -sf /etc/nginx/sites-available/zenvillage.live.conf /etc/nginx/sites-enabled/zenvillage.live.conf
    nginx -t && systemctl reload nginx
  '
  echo "⚠  Re-run certbot to restore SSL:"
  echo "   ssh root@${SERVER_IP} 'certbot --nginx -d zenvillage.live -d www.zenvillage.live --redirect --reinstall -n'"
fi

echo "→ fix perms + reload nginx (no config change)"
ssh $SSH_OPTS "root@${SERVER_IP}" '
  chown -R www-data:www-data /var/www/zenvillage-live
  chmod -R 755 /var/www/zenvillage-live
  systemctl reload nginx
'

echo "→ smoke test on live HTTPS (informational — non-fatal)"
smoke() { curl -s -o /dev/null -w "  $1 → HTTP %{http_code}\n" "$1" || true; }
smoke https://zenvillage.live/peace/
smoke https://zenvillage.live/peace/reign-dance-movement.png
smoke https://zenvillage.live/peace/thanks/
smoke https://zenvillage.live/peace/menu/
smoke https://zenvillage.live/manage/
smoke https://zenvillage.live/buy/
smoke https://zenvillage.live/reset/
smoke https://zenvillage.live/reset/affiliate-signup

echo
echo "✓ Public:  https://zenvillage.live/peace"
echo "✓ Menu:    https://zenvillage.live/peace/menu/"
echo "✓ Buy:     https://zenvillage.live/buy/?item={id}"
echo "✓ Manage:  https://zenvillage.live/manage/  (admin key required)"
echo "✓ Reset:   https://zenvillage.live/reset"
echo "✓ Apply:   https://zenvillage.live/reset/affiliate-signup"
echo
echo "→ Founding affiliate ref links (seed first via:"
echo "    ssh root@${SERVER_IP} 'cd /opt/fpai/apps/zen-village && python3 scripts/seed_founding_partners.py'"
echo "  )"
echo "    Atlas:  https://zenvillage.live/reset?ref=ATLAS"
echo "    Halley: https://zenvillage.live/reset?ref=HALLEY"
