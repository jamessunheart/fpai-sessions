#!/usr/bin/env bash
# scripts/psql.sh — quick shell into the streasury schema using the env file.
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/streasury-bot/streasury.env}"

if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -E '^[A-Z_]+=' "${ENV_FILE}")
    set +a
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "DATABASE_URL not set. Source your local .env or pass it." >&2
    exit 1
fi

exec psql "${DATABASE_URL}" \
    -P 'pager=off' \
    -c 'SET search_path TO streasury, public;' \
    "$@"
