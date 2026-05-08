#!/usr/bin/env bash
# Re-deploy fullpotential.com/peace/ static page to primary FPAI server.
#
# Usage:  ./deploy.sh
#
# Adds files only — does NOT use rsync --delete on /peace/ to avoid
# accidentally removing future server-side additions. (Lesson learned
# from the zenvillage-peace deploy in this same worktree.)
#
# Assumes:
#   - SSH key at ~/.ssh/fpai_deploy_ed25519
#   - fullpotential.com nginx vhost already serves
#       /opt/fpai/core/applications/website-ai/frontend/fullpotential-com
#     (verified 2026-05-08 via cat /etc/nginx/sites-enabled/fullpotential.com)
#   - Default location block routes /peace/ via try_files (no nginx
#     config change needed)
#
# Idempotent. Safe to re-run.

set -euo pipefail

SERVER_IP="198.54.123.234"
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"
DEPLOY_PATH="/opt/fpai/core/applications/website-ai/frontend/fullpotential-com"

cd "$(dirname "$0")"

echo "→ rsync /peace/ to fullpotential.com (additive, no --delete)"
rsync -avz -e "ssh $SSH_OPTS" peace/ "root@${SERVER_IP}:${DEPLOY_PATH}/peace/"

echo "→ fix perms + reload nginx"
ssh $SSH_OPTS "root@${SERVER_IP}" "
  chown -R www-data:www-data ${DEPLOY_PATH}/peace
  chmod -R 755 ${DEPLOY_PATH}/peace
  systemctl reload nginx
"

echo "→ smoke test on live HTTPS"
curl -sf -o /dev/null -w "  https://fullpotential.com/peace/ → HTTP %{http_code}\n" https://fullpotential.com/peace/

echo
echo "✓ Live: https://fullpotential.com/peace/"
