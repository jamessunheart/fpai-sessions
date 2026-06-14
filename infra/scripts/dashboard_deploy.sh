#!/usr/bin/env bash
# ───────────────────────────────────────────────────────────────
# Ember Dashboard deploy
# Builds JSON from DASHBOARD.md → rsyncs static page to fullpotential.com/dashboard
# Auth: nginx basic-auth (location /dashboard · same .htpasswd as /admin /dashboards)
# Trust-tier 4.1 · reversible · uses fpai_deploy_ed25519
# ───────────────────────────────────────────────────────────────
set -euo pipefail

REPO="/Users/jamessunheart/FPAI_Cockpit"
SRC="${REPO}/SERVICES/dashboard-page"
REMOTE_HOST="198.54.123.234"
REMOTE_USER="${DASHBOARD_DEPLOY_USER:-root}"
REMOTE_PATH="/opt/fpai/core/applications/website-ai/frontend/dashboard"
SSH_KEY="${HOME}/.ssh/fpai_deploy_ed25519"
DRY_RUN="${DRY_RUN:-0}"

ts() { date "+%Y-%m-%d %H:%M:%S"; }
log() { echo "[$(ts)] $*"; }

log "build · DASHBOARD.md → dashboard.json"
python3 "${REPO}/infra/scripts/dashboard_build.py"

log "verify artifacts present"
for f in index.html dashboard.json robots.txt; do
  if [[ ! -f "${SRC}/${f}" ]]; then
    log "ERROR: missing ${SRC}/${f}"
    exit 1
  fi
done

RSYNC_FLAGS=(-avz --delete --no-perms --no-owner --no-group)
if [[ "${DRY_RUN}" == "1" ]]; then
  RSYNC_FLAGS+=(--dry-run)
  log "DRY-RUN mode active"
fi

if [[ ! -f "${SSH_KEY}" ]]; then
  log "WARN: ${SSH_KEY} not found · falling back to default agent"
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new"
else
  SSH_CMD="ssh -i ${SSH_KEY} -o StrictHostKeyChecking=accept-new"
fi

log "ensure remote path exists: ${REMOTE_PATH}"
${SSH_CMD} "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_PATH}"

log "rsync ${SRC}/  →  ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"
rsync "${RSYNC_FLAGS[@]}" -e "${SSH_CMD}" \
  --exclude '.DS_Store' \
  "${SRC}/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"

log "deploy complete · https://fullpotential.com/dashboard (auth-gated)"
log "first-time setup checklist printed below"

cat <<'EOF'

──────── FIRST-TIME NGINX WIRE (ONE-TIME on server) ────────
Add to /etc/nginx/sites-available/fullpotential (or wherever the main server block lives),
inside the `server { listen 443 ssl ... }` block, BEFORE the catchall `location /`:

    # ====================================================
    # 🌒 EMBER DASHBOARD (James-auth-gated · read-only)
    # ====================================================
    location /dashboard {
        auth_basic "Ember Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;

        alias /opt/fpai/core/applications/website-ai/frontend/dashboard;
        try_files $uri $uri/ /dashboard/index.html;

        # cache discipline · always re-fetch JSON; HTML can cache briefly
        location ~* \.json$ {
            auth_basic "Ember Dashboard";
            auth_basic_user_file /etc/nginx/.htpasswd;
            add_header Cache-Control "no-store, no-cache, must-revalidate" always;
            add_header X-Robots-Tag "noindex, nofollow" always;
            expires off;
        }

        add_header X-Robots-Tag "noindex, nofollow" always;
        add_header X-Frame-Options "DENY" always;
        add_header Referrer-Policy "no-referrer" always;
    }

Then on the server:
    nginx -t && systemctl reload nginx

If the .htpasswd line doesn't include James yet:
    htpasswd /etc/nginx/.htpasswd james   # prompts for password
─────────────────────────────────────────────────────────────
EOF
