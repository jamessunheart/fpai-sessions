#!/bin/bash
# Quick status check - See everything at a glance

echo "🔍 SYSTEM STATUS CHECK"
echo "====================="
echo ""

# Treasury
echo "💰 TREASURY:"
cd /Users/jamessunheart/Development/docs/coordination/scripts
./overnight-guardian.sh 2>&1 | grep -E "(BTC|SOL|matches|revenue)" | head -4
echo ""

# Services
echo "🌐 SERVICES:"
if curl -s --max-time 2 http://198.54.123.234:8401/health > /dev/null 2>&1; then
    echo "  I MATCH: 🟢 Live"
else
    echo "  I MATCH: 🔴 Down"
fi

if curl -s --max-time 2 http://198.54.123.234:8401/contribute/join-movement > /dev/null 2>&1; then
    echo "  Contribution System: 🟢 Live"
else
    echo "  Contribution System: 🔴 Down"
fi
echo ""

# Outreach
echo "📣 OUTREACH:"
if [ -f /Users/jamessunheart/Development/SERVICES/i-match/outreach_agent.pid ]; then
    PID=$(cat /Users/jamessunheart/Development/SERVICES/i-match/outreach_agent.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "  Autonomous Agent: 🟢 Running (PID: $PID)"
    else
        echo "  Autonomous Agent: 🟡 Stopped"
    fi
else
    echo "  Autonomous Agent: 🟡 Not started"
fi

if [ -n "$REDDIT_CLIENT_ID" ]; then
    echo "  Reddit Credentials: ✅ Set"
else
    echo "  Reddit Credentials: ❌ Not set"
fi
echo ""

# Monitoring
echo "🔔 MONITORING:"
if crontab -l 2>/dev/null | grep -q "overnight-guardian"; then
    echo "  Cron Monitoring: ✅ Active"
else
    echo "  Cron Monitoring: ❌ Not active"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Quick Actions:"
echo "  • Activate Reddit: cat _guides/activation/OUTREACH_INTEGRATION_GUIDE.md"
echo "  • View Dashboard: cat DASHBOARD.md"
echo "  • Quick Start: ./_scripts/quick-start.sh"
echo ""
