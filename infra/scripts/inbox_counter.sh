#!/bin/bash
# inbox_counter.sh — emit the 1-line inbox counter for Ember's alignment footer
#
# Ember reads this at each substantive reply. Cheap (<50ms).
# Format: "📥 INBOX · N pending · K high-lev [· W WIP]"
# Empty: "📥 INBOX · empty"

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INBOX_PY="${SCRIPT_DIR}/veto_inbox.py"

if [ ! -f "$INBOX_PY" ]; then
    echo "📥 INBOX · (engine missing)"
    exit 0
fi

OUT=$(python3 "$INBOX_PY" counter 2>/dev/null || echo "")
if [ -z "$OUT" ] || [ "$OUT" = "0 pending" ]; then
    echo "📥 INBOX · empty"
else
    echo "📥 INBOX · ${OUT}"
fi
