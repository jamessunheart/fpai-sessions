#!/usr/bin/env bash
# Guarded maintenance pass for d201: repair server-162 certbot when
# pyOpenSSL and cryptography are incompatible.
set -euo pipefail

SPEC_ID="SPEC_d201_infra-certbot-pyopenssl-cryptog"
APPROVAL="${D201_CERTBOT_MAINTENANCE_APPROVED:-0}"
STRATEGY="${D201_CERTBOT_STRATEGY:-}"
DRY_RUN="${D201_DRY_RUN:-0}"
DISABLE_FILE="${D201_DISABLE_FILE:-/opt/fpai-build/.d201_certbot_fix_disabled}"
BACKUP_ROOT="${D201_BACKUP_ROOT:-/opt/fpai-build/backups/d201-certbot}"
LOG_DIR="${D201_LOG_DIR:-/opt/fpai-build/logs}"
LOG_FILE="${D201_LOG_FILE:-$LOG_DIR/${SPEC_ID}.log}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CERTBOT_BIN="${CERTBOT_BIN:-}"

log() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG_FILE"
}

run() {
  log "+ $*"
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  "$@"
}

find_certbot() {
  if [[ -n "$CERTBOT_BIN" ]]; then
    printf '%s\n' "$CERTBOT_BIN"
    return 0
  fi
  command -v certbot
}

require_server_162() {
  if [[ "${D201_ALLOW_NON_162:-0}" == "1" || "${FPAI_SERVER_ID:-}" == "162" ]]; then
    return 0
  fi
  if hostname -I 2>/dev/null | tr ' ' '\n' | grep -qx '162.0.208.88'; then
    return 0
  fi
  log "refusing: this maintenance script is scoped to server 162; set D201_ALLOW_NON_162=1 only for tests"
  exit 1
}

certbot_python() {
  local certbot="$1"
  local shebang
  shebang="$(head -n 1 "$certbot" 2>/dev/null || true)"
  if [[ "$shebang" != '#!'*python* ]]; then
    log "refusing: $certbot does not expose a Python shebang; choose snap-refresh or pipx-reinstall manually"
    exit 1
  fi
  shebang="${shebang#\#!}"
  printf '%s\n' "${shebang%% *}"
}

backup_python_env() {
  local python="$1"
  local backup_dir="$BACKUP_ROOT/$(date -u +%Y%m%dT%H%M%SZ)"
  run mkdir -p "$backup_dir"
  log "writing Python package snapshot to $backup_dir/pip-freeze.before.txt"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "+ $python -m pip freeze > $backup_dir/pip-freeze.before.txt"
    return 0
  fi
  "$python" -m pip freeze > "$backup_dir/pip-freeze.before.txt"
}

apply_fix() {
  local certbot="$1"
  local python
  case "$STRATEGY" in
    venv-upgrade)
      python="$(certbot_python "$certbot")"
      backup_python_env "$python"
      run "$python" -m pip install --upgrade 'pyOpenSSL>=24.0.0' 'cryptography>=41,<46'
      ;;
    system-pip-upgrade)
      if [[ "${D201_ALLOW_SYSTEM_PIP:-0}" != "1" ]]; then
        log "refusing: system-pip-upgrade requires D201_ALLOW_SYSTEM_PIP=1"
        exit 1
      fi
      backup_python_env "$PYTHON_BIN"
      run "$PYTHON_BIN" -m pip install --upgrade --break-system-packages 'pyOpenSSL>=24.0.0' 'cryptography>=41,<46'
      ;;
    snap-refresh)
      if [[ "$DRY_RUN" == "1" ]] || ! snap list certbot >/dev/null 2>&1; then
        run snap install certbot --classic
      fi
      run snap refresh certbot
      ;;
    pipx-reinstall)
      run pipx install --force certbot
      run pipx inject certbot certbot-nginx
      ;;
    *)
      log "refusing: set D201_CERTBOT_STRATEGY to venv-upgrade, system-pip-upgrade, snap-refresh, or pipx-reinstall"
      exit 2
      ;;
  esac
}

prove_certbot() {
  local certbot="$1"
  run "$certbot" --version
  run "$certbot" renew --dry-run
  run "$SYSTEMCTL" reset-failed certbot.service
  run "$SYSTEMCTL" start certbot.service
  run "$SYSTEMCTL" is-active certbot.timer
  run "$SYSTEMCTL" status certbot.timer --no-pager
  log "proof complete: certbot renew --dry-run succeeded; certbot.service start exited 0; certbot.timer is active"
}

main() {
  mkdir -p "$LOG_DIR"
  log "$SPEC_ID starting"

  if [[ -f "$DISABLE_FILE" ]]; then
    log "hold: $DISABLE_FILE exists"
    exit 0
  fi

  if [[ "$APPROVAL" != "1" ]]; then
    log "hold: set D201_CERTBOT_MAINTENANCE_APPROVED=1 during the approved maintenance pass"
    log "no package changes were made"
    exit 0
  fi

  require_server_162

  local certbot
  certbot="$(find_certbot)"
  if [[ ! -x "$certbot" ]]; then
    log "failed: certbot binary is missing or not executable: $certbot"
    exit 1
  fi

  log "certbot=$certbot strategy=$STRATEGY dry_run=$DRY_RUN"
  apply_fix "$certbot"
  prove_certbot "$certbot"
  log "$SPEC_ID complete"
}

main "$@"
