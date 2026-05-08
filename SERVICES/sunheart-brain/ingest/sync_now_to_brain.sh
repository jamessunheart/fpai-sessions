#!/usr/bin/env bash
# Push core/STATE/NOW.md as a Sunheart Brain note (source=now-log).
# Idempotency key: source_id = now-<UTC ISO timestamp>, so each invocation
# creates a new timeline entry. To overwrite the latest in place, set
# SOURCE_ID=now-current before running.
#
# Auth:
#   Reads bearer token from ~/.config/sh-brain/ingest.token.bare (mode 600).
#   Bare token only — no labels. Pull from server with:
#     ssh root@162.0.208.88 \
#       "grep -E '^Token:' /root/sh-brain-secrets/token-ingest.txt | awk '{print \$NF}'" \
#       > ~/.config/sh-brain/ingest.token.bare
#     chmod 600 ~/.config/sh-brain/ingest.token.bare
#
# Usage: ./sync_now_to_brain.sh [path-to-now.md]
set -euo pipefail

NOW_FILE="${1:-/Users/jamessunheart/FPAI_Cockpit/core/STATE/NOW.md}"
TOKEN_FILE="${HOME}/.config/sh-brain/ingest.token.bare"
ENDPOINT="https://brain.sunheart.com/index/ingest/add_note"

[ -f "$NOW_FILE" ]   || { echo "missing: $NOW_FILE"; exit 1; }
[ -f "$TOKEN_FILE" ] || { echo "missing: $TOKEN_FILE  (see header for setup)"; exit 1; }

TOKEN=$(cat "$TOKEN_FILE")
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SOURCE_ID="${SOURCE_ID:-now-$TIMESTAMP}"

PAYLOAD=$(NOW_FILE="$NOW_FILE" SOURCE_ID="$SOURCE_ID" TIMESTAMP="$TIMESTAMP" python3 - <<'PYEOF'
import json, os
with open(os.environ["NOW_FILE"]) as f:
    content = f.read()
print(json.dumps({
    "source": "now-log",
    "source_id": os.environ["SOURCE_ID"],
    "title": f"NOW snapshot — {os.environ['TIMESTAMP']}",
    "content": content,
    "tags": ["now", "snapshot", "state", "integrated-view"],
    "note_type": "snapshot",
    "sensitivity": "🟢 Public",
    "prefer": "local",
}))
PYEOF
)

curl -fsS --max-time 90 -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "$ENDPOINT"
echo

# Also drop the file on the brain server so the Telegram bot can read it
# directly (used by /projects → PROJECT RANKING parser). Best-effort scp.
BRAIN_HOST="${BRAIN_HOST:-root@162.0.208.88}"
BRAIN_STATE_DIR="${BRAIN_STATE_DIR:-/var/lib/sh-brain/state}"
ssh -o ConnectTimeout=5 "$BRAIN_HOST" "mkdir -p $BRAIN_STATE_DIR" >/dev/null 2>&1 \
    && scp -o ConnectTimeout=5 -q "$NOW_FILE" "$BRAIN_HOST:$BRAIN_STATE_DIR/NOW.md" \
    && echo "synced NOW.md → $BRAIN_HOST:$BRAIN_STATE_DIR/" \
    || echo "warn: file-sync to $BRAIN_HOST failed (note still pushed via API)"

# Sync CAPABILITIES.md alongside (read by /capabilities on @sunheartbrain_bot).
CAP_FILE="$(dirname "$NOW_FILE")/CAPABILITIES.md"
if [ -f "$CAP_FILE" ]; then
    scp -o ConnectTimeout=5 -q "$CAP_FILE" "$BRAIN_HOST:$BRAIN_STATE_DIR/CAPABILITIES.md" \
        && echo "synced CAPABILITIES.md → $BRAIN_HOST:$BRAIN_STATE_DIR/" \
        || echo "warn: CAPABILITIES.md scp failed"
fi
