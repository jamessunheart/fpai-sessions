#!/bin/bash

# Session Report to SSOT
# Each session can run this to report its status and update SSOT

# Source SSOT location
SSOT_LOCATION="/Users/jamessunheart/Development/docs/coordination/.ssot-location"
if [ -f "$SSOT_LOCATION" ]; then
    source "$SSOT_LOCATION"
else
    echo "❌ Cannot find SSOT location file"
    exit 1
fi

# Get session information
SESSION_ID="${1:-unknown}"
ACTION="${2:-reporting}"
TARGET="${3:-SSOT update}"
PHASE="${4:-Updating system state}"

echo "📊 Reporting to SSOT..."
echo "  Session: $SESSION_ID"
echo "  Action: $ACTION"
echo ""

# 1. Update SSOT with current system state
if [ -x "$SSOT_UPDATE_SCRIPT" ]; then
    "$SSOT_UPDATE_SCRIPT"
    echo "✅ SSOT updated with current state"
else
    echo "⚠️  SSOT update script not found"
fi

# 2. Register session if not already registered
SESSION_DIR="$SSOT_DIR/sessions"
if [ ! -f "$SESSION_DIR/${SESSION_ID}.json" ] && [ "$SESSION_ID" != "unknown" ]; then
    echo "  Registering session in coordination..."
    ./docs/coordination/scripts/session-start.sh "$ACTION" "$TARGET" 2>/dev/null || true
fi

# 3. Send heartbeat
if [ "$SESSION_ID" != "unknown" ]; then
    echo "  Sending heartbeat..."
    ./docs/coordination/scripts/session-heartbeat.sh "$ACTION" "$TARGET" "$PHASE" "" "SSOT updated" 2>/dev/null || true
fi

# 4. Display current SSOT state
echo ""
echo "📊 Current SSOT State:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$SSOT_FILE" ]; then
    TOTAL=$(jq -r '.session_count.total_processes' "$SSOT_FILE" 2>/dev/null || echo "?")
    REGISTERED=$(jq -r '.session_count.registered' "$SSOT_FILE" 2>/dev/null || echo "?")
    ACTIVE=$(jq -r '.session_count.active' "$SSOT_FILE" 2>/dev/null || echo "?")
    IDLE=$(jq -r '.session_count.idle' "$SSOT_FILE" 2>/dev/null || echo "?")
    LAST_UPDATE=$(jq -r '.last_update' "$SSOT_FILE" 2>/dev/null || echo "?")

    echo "  Total Sessions:    $TOTAL"
    echo "  Registered:        $REGISTERED"
    echo "  Active:            $ACTIVE"
    echo "  Idle:              $IDLE"
    echo "  Last Updated:      $LAST_UPDATE"
else
    echo "  ⚠️  SSOT file not found"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Report complete!"
