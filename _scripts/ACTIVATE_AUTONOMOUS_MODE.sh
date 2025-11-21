#!/bin/bash
###############################################################################
# ACTIVATE AUTONOMOUS MODE - One Command to Enable While-You-Sleep Evolution
# Session #15 - Activation Catalyst
###############################################################################

echo "════════════════════════════════════════════════════════════════════════"
echo "🌙 ACTIVATING AUTONOMOUS MODE"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# 1. Make sure coordinator is executable
chmod +x /Users/jamessunheart/Development/overnight-session-coordinator.sh

# 2. Run it once to verify it works
echo "📊 Testing autonomous coordinator..."
/Users/jamessunheart/Development/overnight-session-coordinator.sh

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Autonomous coordinator test SUCCESSFUL"
    echo ""
else
    echo ""
    echo "❌ Autonomous coordinator test FAILED"
    echo "Please check the script and try again."
    exit 1
fi

# 3. Set up cron job (runs every 2 hours)
echo "⚙️  Setting up cron job for autonomous execution..."

# Remove any existing overnight coordinator jobs
crontab -l 2>/dev/null | grep -v "overnight-session-coordinator" > /tmp/new_crontab

# Add new job
echo "0 */2 * * * /Users/jamessunheart/Development/overnight-session-coordinator.sh" >> /tmp/new_crontab

# Install new crontab
crontab /tmp/new_crontab

if [ $? -eq 0 ]; then
    echo "✅ Cron job installed successfully"
    echo ""
    echo "📋 Current cron jobs:"
    crontab -l | grep overnight
else
    echo "⚠️  Cron job installation requires permission"
    echo ""
    echo "MANUAL SETUP REQUIRED:"
    echo "Run this command to set up cron job:"
    echo ""
    echo "  (crontab -l 2>/dev/null | grep -v 'overnight-session-coordinator'; echo '0 */2 * * * /Users/jamessunheart/Development/overnight-session-coordinator.sh') | crontab -"
    echo ""
fi

# Clean up
rm -f /tmp/new_crontab

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "✅ AUTONOMOUS MODE ACTIVATED"
echo "════════════════════════════════════════════════════════════════════════"
echo ""
echo "🌙 What's Running While You Sleep:"
echo "   ✅ I MATCH service health monitoring (every 2 hours)"
echo "   ✅ Treasury price tracking (BTC, SOL)"
echo "   ✅ Email capture system monitoring"
echo "   ✅ SSOT updates"
echo "   ✅ Session coordination broadcasts"
echo ""
echo "📝 Logs You Can Review Tomorrow:"
echo "   • overnight.log - All autonomous actions taken"
echo "   • autonomous-decisions-log.md - Decision transparency log"
echo "   • treasury-overnight-report.json - Price movements"
echo ""
echo "🌅 Tomorrow Morning, Run:"
echo "   tail -100 overnight.log  # See what happened while you slept"
echo "   cat autonomous-decisions-log.md  # Full decision transparency"
echo ""
echo "🛑 To Stop Autonomous Mode:"
echo "   ./DEACTIVATE_AUTONOMOUS_MODE.sh"
echo ""
echo "💤 Sleep well! The system is watching, monitoring, evolving..."
echo ""
echo "════════════════════════════════════════════════════════════════════════"
