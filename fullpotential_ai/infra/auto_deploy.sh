#!/bin/bash
#
# Simple auto-deploy helper. Intended to be triggered by cron every minute.
# Pulls the latest changes from origin/main and restarts optional services.

set -euo pipefail

TARGET_DIR="${FPAI_DEPLOY_DIR:-/opt/fpai}"
LOG_DIR="${FPAI_DEPLOY_LOG_DIR:-/var/log/fpai}"
LOG_FILE="${LOG_DIR}/deploy.log"

mkdir -p "${LOG_DIR}"

{
  echo "---"
  echo "Auto deploy tick @ $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

  if [[ ! -d "${TARGET_DIR}/.git" ]]; then
    echo "Target dir ${TARGET_DIR} is not a git repo; skipping."
    exit 0
  fi

  cd "${TARGET_DIR}"
  git fetch origin main

  LOCAL_HASH="$(git rev-parse HEAD)"
  REMOTE_HASH="$(git rev-parse origin/main)"

  if [[ "${LOCAL_HASH}" == "${REMOTE_HASH}" ]]; then
    echo "Already up to date."
    exit 0
  fi

  git reset --hard origin/main
  echo "Updated to ${REMOTE_HASH}"

  # Optional: restart services when new code lands
  if command -v systemctl >/dev/null 2>&1; then
    # systemctl restart fpai-orchestrator.service || true
    :
  fi
} >> "${LOG_FILE}" 2>&1


