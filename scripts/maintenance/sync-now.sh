#!/bin/bash
# sync-now.sh — Push local NOW.md (source of truth) to Adam on server 162.0.208.88
#
# Usage:
#   ./sync-now.sh             # push current core/STATE/NOW.md to server
#   ./sync-now.sh --check     # verify server copy matches local without pushing
#   ./sync-now.sh --pull      # pull server copy back (emergency revert)
#
# The server path /opt/fpai/NOW.md is the single source on the server.
# /opt/fpai/openclaw/workspace/NOW.md is a symlink to it.

set -e

LOCAL_NOW="$(cd "$(dirname "$0")" && pwd)/core/STATE/NOW.md"
SERVER="root@162.0.208.88"
SERVER_NOW="/opt/fpai/NOW.md"

if [ ! -f "$LOCAL_NOW" ]; then
  echo "❌ Local NOW.md not found at: $LOCAL_NOW" >&2
  exit 1
fi

case "${1:-push}" in
  --check|check)
    echo "Comparing local ↔ server NOW.md..."
    DIFF=$(diff "$LOCAL_NOW" <(ssh -o ConnectTimeout=10 "$SERVER" "cat $SERVER_NOW") || true)
    if [ -z "$DIFF" ]; then
      echo "✓ In sync"
      exit 0
    fi
    echo "⚠ Drift detected:"
    echo "$DIFF" | head -40
    echo ""
    echo "Run './sync-now.sh' to push local → server, or './sync-now.sh --pull' to pull server → local."
    exit 2
    ;;

  --pull|pull)
    echo "Pulling server $SERVER_NOW → $LOCAL_NOW ..."
    cp "$LOCAL_NOW" "${LOCAL_NOW}.bak-$(date -u +%s)"
    scp -o ConnectTimeout=10 "$SERVER:$SERVER_NOW" "$LOCAL_NOW"
    echo "✓ Pulled (local backup saved)"
    ;;

  push|"")
    echo "Pushing $LOCAL_NOW → $SERVER:$SERVER_NOW ..."
    ssh -o ConnectTimeout=10 "$SERVER" "cp $SERVER_NOW ${SERVER_NOW}.bak-\$(date -u +%s)"
    scp -o ConnectTimeout=10 "$LOCAL_NOW" "$SERVER:$SERVER_NOW"
    VERIFY=$(diff "$LOCAL_NOW" <(ssh -o ConnectTimeout=10 "$SERVER" "cat $SERVER_NOW") || true)
    if [ -z "$VERIFY" ]; then
      echo "✓ Pushed and verified. Adam will read the new NOW.md on his next session."
    else
      echo "❌ Push completed but verification diff is non-empty. Investigate." >&2
      exit 3
    fi
    ;;

  *)
    echo "Usage: $0 [push|--check|--pull]" >&2
    exit 1
    ;;
esac
