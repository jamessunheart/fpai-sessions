#!/bin/bash
# Quick view of all active sessions

echo ""
echo "🆔 SESSION REGISTRY - Who's Who"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Extract sessions from registry
awk '/### Session #/,/^$/' ~/Development/MEMORY/SESSION_REGISTRY.md | \
    grep -E "^### Session|^\*\*ID:|^\*\*Purpose:|^\*\*Status:" | \
    sed 's/^### //' | \
    sed 's/^\*\*/  /' | \
    sed 's/\*\*$//'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📖 Full registry: cat MEMORY/SESSION_REGISTRY.md"
echo "🔄 Full state: cat MEMORY/CURRENT_STATE.md"
echo ""
