#!/bin/bash
# 🌙 Autonomous Night Evolution - Run this before bed
# Session #2 - Continuous Improvement System
#
# This script runs autonomous optimization cycles while you sleep.
# In the morning, check morning_briefing.md for complete summary.
#
# Usage:
#   ./run-while-you-sleep.sh           # Full night (20 cycles, ~10 hours)
#   ./run-while-you-sleep.sh --test    # Single test cycle (5 minutes)

cd /Users/jamessunheart/Development/SERVICES

echo "🌙 Autonomous Night Evolution Starting..."
echo ""
echo "⏰ This will run optimization cycles while you sleep"
echo "📊 Morning briefing will be ready when you wake up"
echo ""

# Determine mode
if [ "$1" == "--test" ]; then
    echo "🧪 TEST MODE: Running single cycle (~5 minutes)"
    python3 autonomous-night-optimizer.py --once
else
    echo "🌙 NIGHT MODE: Running 20 cycles (~10 hours)"
    echo "💤 Go to sleep - the system will keep evolving"
    echo ""
    python3 autonomous-night-optimizer.py
fi

echo ""
echo "✅ Autonomous evolution complete!"
echo "📋 Check morning_briefing.md for full summary"
echo ""
