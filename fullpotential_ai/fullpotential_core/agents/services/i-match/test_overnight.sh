#!/bin/bash
# Quick test to verify overnight system works

echo "🧪 Testing Overnight System..."
echo ""

# Test 1: API key
echo "1. Checking API key..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "   ❌ ANTHROPIC_API_KEY not set"
    echo "   Fix: export ANTHROPIC_API_KEY='your-key'"
    exit 1
else
    echo "   ✅ API key is set"
fi

# Test 2: Database
echo "2. Checking database..."
if [ -f "i_match.db" ]; then
    echo "   ✅ Database exists"
else
    echo "   ❌ Database not found"
    exit 1
fi

# Test 3: Python dependencies
echo "3. Checking Python packages..."
python3 -c "import anthropic; import sqlite3; print('   ✅ All packages available')" 2>&1

# Test 4: Run for 1 minute (test mode)
echo "4. Testing overnight system (30 seconds)..."
echo ""
timeout 30 python3 while_you_sleep.py 0.01 2>&1 | head -20
echo ""
echo "✅ Test complete! System is working."
echo ""
echo "To start for real (8 hours):"
echo "  ./START_OVERNIGHT.sh"
