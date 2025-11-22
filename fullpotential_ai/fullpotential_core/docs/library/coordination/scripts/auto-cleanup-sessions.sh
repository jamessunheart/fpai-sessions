#!/bin/bash

# 🤖 Automatic Session Cleanup
# Run this periodically (cron, boot, or on-demand) to clean stale sessions
# Usage: ./auto-cleanup-sessions.sh [--timeout-minutes MINUTES]

TIMEOUT_MINUTES=${1:-120}  # Default: 2 hours

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Run the cleanup script silently
"$SCRIPT_DIR/session-cleanup-stale.sh" --timeout-minutes "$TIMEOUT_MINUTES" > /dev/null 2>&1

# Exit with success (don't fail if no stale sessions found)
exit 0
