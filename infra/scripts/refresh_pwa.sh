#!/bin/bash
# refresh_pwa.sh — regenerate inbox.json for the Veto Inbox PWA
#
# Dumps current queue + recent resolved as JSON next to the PWA static files.
# Called manually OR by a watcher OR after each producer add (cheap; <100ms).
#
# Reversibility: chmod -x this script and PWA shows stale data; queue still works.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INBOX_PY="${SCRIPT_DIR}/veto_inbox.py"
PWA_DIR="${SCRIPT_DIR}/../../SERVICES/veto-inbox-pwa"
OUT="${PWA_DIR}/inbox.json"

if [ ! -f "$INBOX_PY" ]; then
    echo "ERROR: veto_inbox.py not found at $INBOX_PY" >&2
    exit 1
fi
mkdir -p "$PWA_DIR"
python3 "$INBOX_PY" dump_pwa > "${OUT}.tmp" && mv "${OUT}.tmp" "$OUT"
echo "wrote $OUT ($(wc -c < "$OUT") bytes)"
