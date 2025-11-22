#!/bin/bash
# Quick status check for all autonomous systems

echo ""
echo "======================================================================="
echo "🤖 AUTONOMOUS SYSTEMS STATUS"
echo "======================================================================="
echo ""

check_process() {
    if ps -p $1 > /dev/null 2>&1; then
        echo "✅ $2 (PID: $1)"
    else
        echo "❌ $2 (not running)"
    fi
}

# Check each system
LOG_DIR="/Users/jamessunheart/Development/agents/services/i-match/autonomous_logs"

if [ -d "$LOG_DIR" ]; then
    for log in "$LOG_DIR"/*.log; do
        if [ -f "$log" ]; then
            name=$(basename "$log" .log)
            lines=$(wc -l < "$log" 2>/dev/null || echo "0")
            echo "📝 $name: $lines log lines"
        fi
    done
fi

echo ""
echo "======================================================================="
echo "📊 QUICK METRICS"
echo "======================================================================="
echo ""

# Check content library
if [ -f "/Users/jamessunheart/Development/agents/services/i-match/content_library.json" ]; then
    posts=$(python3 -c "import json; print(len(json.load(open('/Users/jamessunheart/Development/agents/services/i-match/content_library.json'))['reddit_posts']))" 2>/dev/null || echo "?")
    echo "📝 Reddit posts ready: $posts"
fi

# Check services
services_up=$(curl -s http://localhost:8401/health > /dev/null 2>&1 && echo "✅" || echo "❌")
echo "🌐 I MATCH service: $services_up"

echo ""
echo "======================================================================="
echo ""
echo "Commands:"
echo "  View logs: tail -f $LOG_DIR/*.log"
echo "  Stop all: pkill -f autonomous"
echo "  Restart: bash AUTONOMOUS_MASTER.sh"
echo ""
