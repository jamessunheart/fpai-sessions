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
rsync -avz --delete -e "ssh $SSH_OPTS" peace/ "root@${SERVER_IP}:${DEPLOY_PATH}/peace/"

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

echo "→ smoke test on live HTTPS"
curl -sf -o /dev/null -w "  https://zenvillage.live/peace/ → HTTP %{http_code}\n" https://zenvillage.live/peace/
curl -sf -o /dev/null -w "  https://zenvillage.live/peace/reign-dance-movement.png → HTTP %{http_code}\n" https://zenvillage.live/peace/reign-dance-movement.png

echo
echo "✓ Live: https://zenvillage.live/peace"
