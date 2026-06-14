#!/bin/bash

# SSOT Watcher - Keeps Single Source of Truth updated every 5 seconds

echo "🔄 Starting SSOT Watcher..."
echo "Updates every 5 seconds"
echo "Press Ctrl+C to stop"
echo ""

count=1

while true; do
    ./docs/coordination/scripts/update-ssot.sh
    echo "[$count] Updated at $(date '+%H:%M:%S')"
    count=$((count + 1))
    sleep 5
done
