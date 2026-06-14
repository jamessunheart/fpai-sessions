#!/bin/bash
###############################################################################
# AUTONOMOUS OUTREACH MONITORING - Quick Commands
###############################################################################

echo "════════════════════════════════════════════════════════════════════════"
echo "🤖 AUTONOMOUS OUTREACH SYSTEM - MONITOR"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# Check if running
if ps aux | grep -v grep | grep autonomous_outreach_manager > /dev/null; then
    echo "✅ Status: RUNNING"
    PID=$(ps aux | grep -v grep | grep autonomous_outreach_manager | awk '{print $2}')
    echo "   Process ID: $PID"
else
    echo "❌ Status: STOPPED"
    echo ""
    echo "To restart:"
    echo "   cd /Users/jamessunheart/Development/SERVICES/i-match"
    echo "   nohup python3 autonomous_outreach_manager.py --run --interval 60 > autonomous_outreach.log 2>&1 &"
    exit 1
fi

echo ""
echo "────────────────────────────────────────────────────────────────────────"
echo ""

# Show stats
cd /Users/jamessunheart/Development/SERVICES/i-match
python3 autonomous_outreach_manager.py --stats

echo ""
echo "────────────────────────────────────────────────────────────────────────"
echo ""
echo "📋 AVAILABLE COMMANDS:"
echo ""
echo "  ./monitor_outreach.sh              # This screen (current status)"
echo "  python3 autonomous_outreach_manager.py --stats   # Just stats"
echo "  tail -f autonomous_outreach.log    # Live log"
echo "  kill $PID                          # Stop autonomous manager"
echo ""
echo "────────────────────────────────────────────────────────────────────────"
echo ""
echo "📊 EXPECTED TIMELINE:"
echo ""
echo "  Hour 6:  First opens (4-5 expected)"
echo "  Hour 24: First replies (1-2 expected)"
echo "  Hour 48: First advisor signup (1 expected)"
echo "  Hour 72: First revenue ($99-199)"
echo ""
echo "  Day 3:   Automated follow-up #1 to non-responders"
echo "  Day 7:   Automated follow-up #2 to non-responders"
echo "  Day 10:  Mark unresponsive, focus on engaged"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
