#!/bin/bash
# Start autonomous overnight system NOW

echo "🌙 Starting While You Sleep system..."
echo ""

cd /Users/jamessunheart/Development/agents/services/i-match

# Make executable
chmod +x while_you_sleep.py

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set"
    echo ""
    echo "Set it with:"
    echo "  export ANTHROPIC_API_KEY='your-key'"
    exit 1
fi

# Start in background
echo "🚀 Launching autonomous system..."
echo ""
echo "This will:"
echo "  - Monitor for customer/provider signups"
echo "  - Auto-create matches when possible"
echo "  - Generate introduction emails"
echo "  - Create Reddit response templates"
echo "  - Generate morning progress report"
echo ""
echo "You'll wake up to: MORNING_PROGRESS_REPORT.md"
echo ""

# Ask for duration
read -p "How many hours will you sleep? [8]: " hours
hours=${hours:-8}

echo ""
echo "Running for $hours hours..."
echo "Logs: overnight_log.txt"
echo ""

# Start
nohup python3 while_you_sleep.py $hours > overnight_runtime.log 2>&1 &

echo "✅ System started (PID: $!)"
echo ""
echo "Monitor progress:"
echo "  tail -f overnight_log.txt"
echo ""
echo "Stop if needed:"
echo "  pkill -f while_you_sleep.py"
echo ""
echo "😴 Sleep well! See you in the morning."
echo ""
