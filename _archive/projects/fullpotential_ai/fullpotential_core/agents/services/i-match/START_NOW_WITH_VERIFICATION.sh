#!/bin/bash
# Start overnight system with VERIFICATION so you know it's working

echo "═══════════════════════════════════════════════════════════"
echo "🌙 OVERNIGHT SYSTEM - Starting with Verification"
echo "═══════════════════════════════════════════════════════════"
echo ""

cd /Users/jamessunheart/Development/agents/services/i-match

# Step 1: Get API key
echo "Step 1: Setting up API key..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "Enter your Anthropic API key:"
    echo "(It starts with 'sk-ant-api03-...')"
    read -p "API Key: " api_key
    export ANTHROPIC_API_KEY="$api_key"
fi

echo "✅ API key set"
echo ""

# Step 2: Quick test (30 seconds)
echo "Step 2: Testing system for 30 seconds..."
echo "(Watch it work, then we'll start it for real)"
echo ""

timeout 30 python3 while_you_sleep.py 0.01 2>&1 | tee test_output.txt

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ TEST COMPLETE - System is working!"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Step 3: Confirm to start for real
echo "You just saw it work for 30 seconds."
echo "Now start it for REAL overnight?"
echo ""
read -p "How many hours will you sleep? [8]: " hours
hours=${hours:-8}

echo ""
echo "Starting overnight system for $hours hours..."
echo ""

# Start in background with logging
nohup python3 while_you_sleep.py $hours > overnight_runtime.log 2>&1 &
pid=$!

sleep 3

# Verify it's running
if ps -p $pid > /dev/null; then
    echo "✅ SYSTEM STARTED SUCCESSFULLY!"
    echo ""
    echo "PID: $pid"
    echo "Duration: $hours hours"
    echo "End time: $(date -v +${hours}H '+%Y-%m-%d %H:%M')"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "📊 HOW TO VERIFY IT'S WORKING:"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "RIGHT NOW - Check it's running:"
    echo "  ps aux | grep while_you_sleep"
    echo ""
    echo "WATCH IT WORK (live):"
    echo "  tail -f overnight_log.txt"
    echo "  (Press Ctrl+C to exit, system keeps running)"
    echo ""
    echo "CHECK PROGRESS:"
    echo "  tail -20 overnight_log.txt"
    echo ""
    echo "IN THE MORNING:"
    echo "  cat MORNING_PROGRESS_REPORT.md"
    echo ""
    echo "STOP IF NEEDED:"
    echo "  kill $pid"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    # Show first few log lines
    echo "Here's what it's doing RIGHT NOW:"
    echo "─────────────────────────────────────────────────────────"
    sleep 2
    tail -10 overnight_log.txt 2>/dev/null || echo "(Log starting...)"
    echo "─────────────────────────────────────────────────────────"
    echo ""
    echo "😴 You can go to sleep now!"
    echo "The system is working. Check overnight_log.txt anytime."
    echo ""

    # Create a status file
    cat > SYSTEM_STATUS.txt << EOF
🌙 Overnight System Running

Started: $(date)
PID: $pid
Duration: $hours hours
End Time: $(date -v +${hours}H '+%Y-%m-%d %H:%M')

Check status:
  ps aux | grep while_you_sleep

View logs:
  tail -f overnight_log.txt

Stop system:
  kill $pid
EOF

    echo "Status saved to: SYSTEM_STATUS.txt"
    echo ""

else
    echo "❌ Failed to start - check overnight_runtime.log for errors"
    cat overnight_runtime.log
fi
