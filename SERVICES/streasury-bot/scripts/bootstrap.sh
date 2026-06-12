#!/usr/bin/env bash
# scripts/bootstrap.sh — first-time setup on the server (idempotent).
#
# Run from the cockpit (deploy.sh shells into the server and calls this), or
# manually if you SSH in for one-off recovery.
set -euo pipefail

SERVICE_DIR="/opt/streasury-bot"
ENV_DIR="/etc/streasury-bot"
ENV_FILE="${ENV_DIR}/streasury.env"
DATA_DIR="/var/lib/streasury-bot"
USER="streasury"

# 1. system user
if ! id "${USER}" >/dev/null 2>&1; then
    useradd --system --home "${SERVICE_DIR}" --shell /usr/sbin/nologin "${USER}"
fi

# 2. directories
mkdir -p "${ENV_DIR}" "${DATA_DIR}" "${SERVICE_DIR}"
chown -R "${USER}:${USER}" "${SERVICE_DIR}" "${DATA_DIR}"
chown -R root:"${USER}" "${ENV_DIR}"
chmod 0750 "${ENV_DIR}"

# 3. env file (admin must populate before first start)
if [[ ! -f "${ENV_FILE}" ]]; then
    install -m 0640 -o root -g "${USER}" "${SERVICE_DIR}/.env.example" "${ENV_FILE}"
    echo "[bootstrap] populate ${ENV_FILE} with real keys before starting the unit"
fi

# 4. venv
if [[ ! -d "${SERVICE_DIR}/.venv" ]]; then
    python3.11 -m venv "${SERVICE_DIR}/.venv"
fi
"${SERVICE_DIR}/.venv/bin/pip" install --upgrade pip wheel >/dev/null
"${SERVICE_DIR}/.venv/bin/pip" install -r "${SERVICE_DIR}/requirements.txt"
chown -R "${USER}:${USER}" "${SERVICE_DIR}"

# 5. apply schema (idempotent)
if [[ -f "${ENV_FILE}" ]] && grep -q '^DATABASE_URL=' "${ENV_FILE}"; then
    DB_URL=$(grep '^DATABASE_URL=' "${ENV_FILE}" | head -1 | cut -d= -f2-)
    if [[ -n "${DB_URL}" && "${DB_URL}" != *changeme* ]]; then
        psql "${DB_URL}" -f "${SERVICE_DIR}/schema/streasury_schema.sql"
    else
        echo "[bootstrap] DATABASE_URL not configured; skipping schema apply"
    fi
fi

# 6. systemd
install -m 0644 "${SERVICE_DIR}/systemd/streasury-bot.service" /etc/systemd/system/streasury-bot.service
systemctl daemon-reload
systemctl enable streasury-bot.service

echo "[bootstrap] done. Edit ${ENV_FILE}, then: systemctl restart streasury-bot"
