#!/bin/bash
# Core Services Stop Script
# Optimized by: Atlas - Session #1

PIDS_FILE="/tmp/fpai_service_pids.txt"

if [ ! -f "$PIDS_FILE" ]; then
    echo "❌ No running services found (no PID file)"
    exit 1
fi

echo "🛑 Stopping Full Potential AI Core Services..."
echo ""

while IFS=: read -r name pid port; do
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "   Stopping $name (PID: $pid, Port: $port)..."
        kill "$pid" 2>/dev/null || echo "   ⚠️  Could not kill PID $pid"
    else
        echo "   ℹ️  $name (PID: $pid) already stopped"
    fi
done < "$PIDS_FILE"

rm "$PIDS_FILE"

echo ""
echo "✅ All services stopped"
