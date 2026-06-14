#!/bin/bash
###############################################################################
# DEACTIVATE AUTONOMOUS MODE - Stop Overnight Monitoring
# Session #15 - Activation Catalyst
###############################################################################

echo "════════════════════════════════════════════════════════════════════════"
echo "🛑 DEACTIVATING AUTONOMOUS MODE"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# Remove cron job
echo "⚙️  Removing cron job..."
crontab -l 2>/dev/null | grep -v "overnight-session-coordinator" | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron job removed"
else
    echo "⚠️  No cron job found or permission denied"
fi

# Stop any running instances
echo ""
echo "🛑 Stopping any running coordinator processes..."
pkill -f overnight-session-coordinator.sh

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "✅ AUTONOMOUS MODE DEACTIVATED"
echo "════════════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Final Logs Available:"
echo "   • overnight.log - What happened during autonomous mode"
echo "   • autonomous-decisions-log.md - All decisions made"
echo ""
echo "🔄 To Reactivate:"
echo "   ./ACTIVATE_AUTONOMOUS_MODE.sh"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
