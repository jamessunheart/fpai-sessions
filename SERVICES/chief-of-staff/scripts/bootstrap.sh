#!/usr/bin/env bash
# Idempotent bootstrap on the brain server: user, venv, env, systemd unit.
set -euo pipefail

DEPLOY_PATH="/opt/chief-of-staff"
ENV_DIR="/etc/chief-of-staff"
SERVICE_NAME="chief-of-staff"
SERVICE_USER="chief"

# 1) user
if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

# 2) env file (skeleton — values can be edited later)
mkdir -p "${ENV_DIR}"
if [[ ! -f "${ENV_DIR}/chief.env" ]]; then
    cat > "${ENV_DIR}/chief.env" <<'EOF'
# Chief of Staff config
COCKPIT_ROOT=/opt/chief-of-staff
SERVICES_SUBDIR=SERVICES
STATE_SUBDIR=state
EOF
fi
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${ENV_DIR}"
chmod 600 "${ENV_DIR}/chief.env"

# 3) venv
if [[ ! -d "${DEPLOY_PATH}/.venv" ]]; then
    python3 -m venv "${DEPLOY_PATH}/.venv"
fi
"${DEPLOY_PATH}/.venv/bin/pip" install --upgrade pip --quiet
"${DEPLOY_PATH}/.venv/bin/pip" install -r "${DEPLOY_PATH}/requirements.txt" --quiet

# 4) ownership
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${DEPLOY_PATH}"

# 5) systemd
install -m 644 "${DEPLOY_PATH}/systemd/${SERVICE_NAME}.service" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}" >/dev/null 2>&1 || true

echo "[bootstrap] done"
