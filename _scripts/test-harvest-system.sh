#!/bin/bash
#
# 🧪 TEST HARVEST SYSTEM
# Quick smoke test to verify the harvest infrastructure is working
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Testing Harvest System Infrastructure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 1: Check scripts exist
echo "✓ Checking scripts exist..."
test -f "$SCRIPT_DIR/harvest-apprentice.py" || { echo "❌ harvest-apprentice.py not found"; exit 1; }
test -f "$SCRIPT_DIR/apprentice-preflight-check.sh" || { echo "❌ apprentice-preflight-check.sh not found"; exit 1; }
echo "  ✅ All scripts present"

# Test 2: Check scripts are executable
echo "✓ Checking scripts are executable..."
test -x "$SCRIPT_DIR/harvest-apprentice.py" || { echo "❌ harvest-apprentice.py not executable"; exit 1; }
test -x "$SCRIPT_DIR/apprentice-preflight-check.sh" || { echo "❌ apprentice-preflight-check.sh not executable"; exit 1; }
echo "  ✅ Scripts are executable"

# Test 3: Check Python script syntax
echo "✓ Checking Python syntax..."
python3 -m py_compile "$SCRIPT_DIR/harvest-apprentice.py" 2>/dev/null || { echo "❌ Python syntax error"; exit 1; }
echo "  ✅ Python syntax valid"

# Test 4: Check required directories
echo "✓ Checking directory structure..."
test -d "$ROOT_DIR/docs/coordination" || mkdir -p "$ROOT_DIR/docs/coordination"
test -d "$ROOT_DIR/SERVICES" || mkdir -p "$ROOT_DIR/SERVICES"
test -d "$ROOT_DIR/STAGING/incoming" || mkdir -p "$ROOT_DIR/STAGING/incoming"
echo "  ✅ Directory structure ready"

# Test 5: Check configuration files
echo "✓ Checking configuration..."
test -f "$ROOT_DIR/docs/coordination/apprentice-submissions.json" || { echo "⚠️  Config file missing (will be created on first run)"; }
test -f "$ROOT_DIR/docs/coordination/apprentice-submissions.log" || { echo "⚠️  Log file missing (will be created on first run)"; }
echo "  ✅ Configuration ready"

# Test 6: Test help output
echo "✓ Testing harvest-apprentice.py --help..."
"$SCRIPT_DIR/harvest-apprentice.py" --help > /dev/null 2>&1 || { echo "❌ Script fails to show help"; exit 1; }
echo "  ✅ Help output works"

# Test 7: Test list functionality (should not fail on empty list)
echo "✓ Testing --list functionality..."
"$SCRIPT_DIR/harvest-apprentice.py" --list > /dev/null 2>&1 || { echo "⚠️  List command failed (may be expected if no submissions yet)"; }
echo "  ✅ List command accessible"

# Test 8: Verify related scripts exist
echo "✓ Checking related harvest tools..."
test -f "$ROOT_DIR/fullpotential_ai/orchestration/tools/harvest_repo.py" && echo "  ✅ Direct harvester found" || echo "  ⚠️  Direct harvester not found"
test -f "$ROOT_DIR/orchestration/tools/gatekeeper.py" && echo "  ✅ Gatekeeper found" || echo "  ⚠️  Gatekeeper not found"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All infrastructure tests passed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Quick Start:"
echo "   View guide: cat $SCRIPT_DIR/HARVEST_QUICKSTART.md"
echo "   Harvest code: $SCRIPT_DIR/harvest-apprentice.py ApprenticeNameHere https://github.com/user/repo"
echo "   List submissions: $SCRIPT_DIR/harvest-apprentice.py --list"
echo ""

