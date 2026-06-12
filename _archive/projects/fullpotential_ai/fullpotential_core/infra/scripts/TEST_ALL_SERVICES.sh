#!/bin/bash

# Master test script for all services
# Tests I PROACTIVE and I MATCH to validate they actually work

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 FULL POTENTIAL AI - SERVICE VALIDATION SUITE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Testing services built from architect's intent:"
echo "  ✓ I PROACTIVE (Droplet #20) - AI Orchestration"
echo "  ✓ I MATCH (Droplet #21) - Revenue Generation"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test I PROACTIVE
echo "📋 Testing I PROACTIVE..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /Users/jamessunheart/Development/agents/services/i-proactive

# Check if dependencies installed
if [ ! -d "venv" ]; then
    echo "📦 Installing I PROACTIVE dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

# Run validation
if python3 validate.py; then
    echo ""
    echo "✅ I PROACTIVE: ALL TESTS PASSED"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo ""
    echo "❌ I PROACTIVE: SOME TESTS FAILED"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo ""
echo ""

# Test I MATCH
echo "📋 Testing I MATCH..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /Users/jamessunheart/Development/agents/services/i-match

# Check if dependencies installed
if [ ! -d "venv" ]; then
    echo "📦 Installing I MATCH dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

# Create .env if needed
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

# Run validation
if python3 validate.py; then
    echo ""
    echo "✅ I MATCH: ALL TESTS PASSED"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo ""
    echo "❌ I MATCH: SOME TESTS FAILED"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Final summary
echo ""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 FINAL RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Services Tested: $TOTAL_TESTS"
echo "  ✅ Passed: $PASSED_TESTS"
echo "  ❌ Failed: $FAILED_TESTS"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 SUCCESS! All services validated and ready to deploy."
    echo ""
    echo "Next steps:"
    echo "  1. Add API keys to .env files (if you want AI features)"
    echo "  2. Start I PROACTIVE: cd agents/services/i-proactive && ./start.sh"
    echo "  3. Start I MATCH: cd agents/services/i-match && ./start.sh"
    echo "  4. Test endpoints: curl http://localhost:8400/health"
    echo ""
else
    echo "⚠️  Some tests failed. Review errors above and fix before deploying."
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
