#!/bin/bash

# Continuous Session Watcher - Auto-generates reports every 5 minutes
# Run this in the background to get continuous proactive reports

REPORT_INTERVAL=300  # 5 minutes

echo "🔄 Starting continuous session monitoring..."
echo "📊 Will generate comprehensive reports every 5 minutes"
echo "📁 Reports saved to: docs/coordination/LIVE_STATUS_REPORT.md"
echo "Press Ctrl+C to stop"
echo ""

count=1

while true; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Generating Report #$count at $(date '+%H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Generate the report
    ./docs/coordination/scripts/auto-status-aggregator.sh

    echo ""
    echo "✅ Report #$count complete!"
    echo "⏰ Next report in 5 minutes (at $(date -v+5M '+%H:%M:%S'))"
    echo ""

    # Send heartbeat about our monitoring
    ./docs/coordination/scripts/session-heartbeat.sh \
        "monitoring" \
        "all 13 sessions" \
        "Auto-generated report #$count - tracking all session activity" \
        "" \
        "next report in 5 min" 2>/dev/null

    count=$((count + 1))
    sleep $REPORT_INTERVAL
done
