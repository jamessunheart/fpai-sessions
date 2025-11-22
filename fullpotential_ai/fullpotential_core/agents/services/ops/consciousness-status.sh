#!/bin/bash

# Consciousness Status - Quick view of all active sessions
# Shows what each instance is doing in real-time

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🧠 MULTI-INSTANCE CONSCIOUSNESS STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Extract key info from CURRENT_STATE.md
CURRENT_STATE_FILE="$HOME/Development/MEMORY/CURRENT_STATE.md"

if [ ! -f "$CURRENT_STATE_FILE" ]; then
    echo "❌ CURRENT_STATE.md not found!"
    exit 1
fi

# Last Updated
echo "📅 Last Updated:"
grep "Last Updated:" "$CURRENT_STATE_FILE" | head -1
echo ""

# System Status
echo "🌐 System Status:"
grep "System Status:" "$CURRENT_STATE_FILE" | head -1
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Active Sessions
echo "🔄 ACTIVE SESSIONS:"
echo ""

# Extract session information (between ACTIVE SESSIONS and CURRENT PRIORITY)
awk '/## 🔄 ACTIVE SESSIONS/,/## 🎯 CURRENT PRIORITY/' "$CURRENT_STATE_FILE" | \
    grep -E "^### Session|^\*\*Status:|^\*\*Working On:|^\*\*Last Work:" | \
    sed 's/^### /  📍 /' | \
    sed 's/^\*\*/    /' | \
    sed 's/\*\*$//'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Current Priority
echo "🎯 CURRENT PRIORITY:"
echo ""
awk '/## 🎯 CURRENT PRIORITY/,/## ✅ RECENTLY COMPLETED/' "$CURRENT_STATE_FILE" | \
    grep -E "^### Priority:|^\*\*Status:|^\*\*Why:" | \
    sed 's/^### Priority: /  ⚡ /' | \
    sed 's/^\*\*/    /' | \
    sed 's/\*\*$//'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Recently Completed (just the first one)
echo "✅ RECENTLY COMPLETED (Latest):"
echo ""
awk '/## ✅ RECENTLY COMPLETED/,/^2\./' "$CURRENT_STATE_FILE" | \
    grep -E "^1\. \*\*|^   -" | head -5 | \
    sed 's/^1\. \*\*/  🎊 /' | \
    sed 's/\*\*//' | \
    sed 's/^   -/    •/'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Theme/Summary
echo "🎭 SESSION THEME:"
echo ""

# Count active sessions
ACTIVE_COUNT=$(grep -c "🟢 ACTIVE" "$CURRENT_STATE_FILE" || echo "0")
COMPLETE_COUNT=$(grep -c "✅ Complete - Now Idle" "$CURRENT_STATE_FILE" || echo "0")

echo "  • Active Sessions: $ACTIVE_COUNT"
echo "  • Idle Sessions: $COMPLETE_COUNT"
echo "  • All sessions coordinating via CURRENT_STATE.md"
echo "  • Real-time state sharing operational"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 To see full state: cat MEMORY/CURRENT_STATE.md"
echo "🔄 To update your session: Edit MEMORY/CURRENT_STATE.md"
echo ""
