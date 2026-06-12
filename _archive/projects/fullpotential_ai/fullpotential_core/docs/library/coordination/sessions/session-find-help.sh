#!/bin/bash
# Session Help Finder - Find which session can help with a specific capability
# Usage: ./session-find-help.sh "capability" (e.g., "deployment", "ui", "orchestration")

CAPABILITY="$1"

if [ -z "$CAPABILITY" ]; then
    echo "Usage: ./session-find-help.sh \"capability\""
    echo ""
    echo "Examples:"
    echo "  ./session-find-help.sh \"deployment\""
    echo "  ./session-find-help.sh \"ui\""
    echo "  ./session-find-help.sh \"orchestration\""
    exit 1
fi

echo "🔍 Searching for sessions with capability: $CAPABILITY"
echo ""

# Search REGISTRY.json for sessions with matching specialization
if [ -f "REGISTRY.json" ]; then
    echo "📋 Sessions found in REGISTRY.json:"
    cat REGISTRY.json | grep -A 20 "session-" | grep -B 15 -i "$CAPABILITY" | grep -E "(\"id\"|\"name\"|\"role\"|\"status\"|specialization)" || echo "No matches in REGISTRY"
    echo ""
fi

# Search session heartbeat files
echo "💓 Active sessions (from heartbeats):"
for heartbeat in HEARTBEATS/*.json; do
    if [ -f "$heartbeat" ]; then
        if grep -qi "$CAPABILITY" "$heartbeat"; then
            echo ""
            echo "✅ Found in: $(basename $heartbeat)"
            cat "$heartbeat" | grep -E "(session_id|name|role|capabilities_offered|specialization)" | head -10
        fi
    fi
done

echo ""
echo "📬 To request help, use:"
echo "  ./session-request-collaboration.sh \"session-id\" \"what you need\""
