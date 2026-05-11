#!/bin/bash
# auto-compress-logs-cron.sh - Setup automatic daily log compression

CRON_SCRIPT="/Users/jamessunheart/Development/docs/coordination/scripts/compress-session-logs.sh"

echo "Setting up automatic daily log compression..."
echo ""
echo "This will run compress-session-logs.sh every day at 11:59 PM"
echo ""

# Create cron job
CRON_JOB="59 23 * * * $CRON_SCRIPT >> /Users/jamessunheart/Development/docs/coordination/DAILY_SUMMARIES/cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "compress-session-logs.sh"; then
    echo "⚠️  Cron job already exists"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep "compress-session-logs.sh"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron job added successfully!"
    echo ""
    echo "Schedule: Daily at 11:59 PM"
    echo "Command: $CRON_SCRIPT"
    echo "Log: /Users/jamessunheart/Development/docs/coordination/DAILY_SUMMARIES/cron.log"
fi

echo ""
echo "📋 To view all cron jobs:"
echo "   crontab -l"
echo ""
echo "🗑️  To remove this cron job:"
echo "   crontab -l | grep -v 'compress-session-logs.sh' | crontab -"
echo ""
echo "▶️  To run manually now:"
echo "   $CRON_SCRIPT"
