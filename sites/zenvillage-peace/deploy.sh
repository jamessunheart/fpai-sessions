#!/usr/bin/env bash
# Re-deploy the zenvillage.live/peace static site to primary FPAI server.
# Usage:  ./deploy.sh
# Idempotent: safe to run any time after editing peace/index.html.

set -euo pipefail

SERVER_IP="198.54.123.234"
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"
DEPLOY_PATH="/var/www/zenvillage-live"

cd "$(dirname "$0")"

echo "→ rsync site files"
rsync -avz --delete -e "ssh $SSH_OPTS" peace/ "root@${SERVER_IP}:${DEPLOY_PATH}/peace/"

echo "→ push nginx config"
scp $SSH_OPTS nginx/zenvillage.live.conf "root@${SERVER_IP}:/etc/nginx/sites-available/zenvillage.live.conf"

echo "→ enable site, fix perms, reload nginx"
ssh $SSH_OPTS "root@${SERVER_IP}" '
  ln -sf /etc/nginx/sites-available/zenvillage.live.conf /etc/nginx/sites-enabled/zenvillage.live.conf
  chown -R www-data:www-data /var/www/zenvillage-live
  chmod -R 755 /var/www/zenvillage-live
  nginx -t && systemctl reload nginx
'

echo "→ smoke test (Host header spoof, since DNS may not be live yet)"
curl -sf -o /dev/null -H "Host: zenvillage.live" "http://${SERVER_IP}/peace/" \
  && echo "✓ /peace/ returns 200 on the server"

echo
echo "Done. If DNS is pointed at ${SERVER_IP}, the site is live at https://zenvillage.live/peace"
