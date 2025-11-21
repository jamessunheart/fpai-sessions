#!/bin/bash

# 🧠 Share Learning - Add discovery to shared knowledge base
# Usage: ./session-share-learning.sh <type> <category> <learning> <impact>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COORD_DIR="$(dirname "$SCRIPT_DIR")"
KNOWLEDGE_DIR="$COORD_DIR/shared-knowledge"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get parameters
TYPE="${1:-learning}"  # learning, pattern, troubleshooting, best-practice
CATEGORY="${2:-General}"
LEARNING="${3}"
IMPACT="${4:-Medium}"

# Validate
if [ -z "$LEARNING" ]; then
    echo "Usage: $0 <type> <category> <learning> <impact>"
    echo ""
    echo "Types:"
    echo "  learning         - General discovery or insight"
    echo "  pattern          - Reusable pattern or approach"
    echo "  troubleshooting  - Problem and solution"
    echo "  best-practice    - Proven effective approach"
    echo ""
    echo "Example:"
    echo "  $0 learning Testing 'pytest --cov shows coverage' 'High'"
    echo "  $0 pattern Development 'Use Pydantic for all validation' 'Critical'"
    exit 1
fi

# Get session ID
SESSION_ID="unknown"
if [ -f "$COORD_DIR/.current_session" ]; then
    SESSION_ID=$(cat "$COORD_DIR/.current_session")
fi

# Get timestamp
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
DATE=$(date -u +"%Y-%m-%d")

# Determine target file
case "$TYPE" in
    learning|learnings)
        TARGET_FILE="$KNOWLEDGE_DIR/learnings.md"
        ENTRY_TITLE="Learning"
        ;;
    pattern|patterns)
        TARGET_FILE="$KNOWLEDGE_DIR/patterns.md"
        ENTRY_TITLE="Pattern"
        ;;
    troubleshooting|trouble|issue)
        TARGET_FILE="$KNOWLEDGE_DIR/troubleshooting.md"
        ENTRY_TITLE="Troubleshooting"
        ;;
    best-practice|practice|best)
        TARGET_FILE="$KNOWLEDGE_DIR/best-practices.md"
        ENTRY_TITLE="Best Practice"
        ;;
    *)
        echo "❌ Unknown type: $TYPE"
        echo "Valid types: learning, pattern, troubleshooting, best-practice"
        exit 1
        ;;
esac

# Create entry file
TEMP_ENTRY=$(mktemp)
cat > "$TEMP_ENTRY" << EOF

### $DATE - $SESSION_ID - $CATEGORY

**$ENTRY_TITLE:** $LEARNING
**Impact:** $IMPACT
**Timestamp:** $TIMESTAMP
**Category:** $CATEGORY
**Shared By:** $SESSION_ID

---
EOF

# Find insertion point and insert
if grep -q "<!-- Sessions add" "$TARGET_FILE"; then
    # Create temp file with entry inserted
    TEMP_FILE=$(mktemp)

    # Read file line by line
    INSERTED=false
    while IFS= read -r line; do
        echo "$line" >> "$TEMP_FILE"
        if [[ "$line" == *"<!-- Sessions add"* ]] && [ "$INSERTED" = false ]; then
            cat "$TEMP_ENTRY" >> "$TEMP_FILE"
            INSERTED=true
        fi
    done < "$TARGET_FILE"

    # Replace original file
    mv "$TEMP_FILE" "$TARGET_FILE"
else
    # Fallback: append to end
    cat "$TEMP_ENTRY" >> "$TARGET_FILE"
fi

# Clean up temp
rm -f "$TEMP_ENTRY"

# Update count at bottom
TOTAL_COUNT=$(grep -c "^### 20" "$TARGET_FILE" 2>/dev/null || echo "0")
if grep -q "**Total.*:**" "$TARGET_FILE"; then
    # Use perl for in-place editing (more reliable than sed on macOS)
    perl -i -pe "s/\*\*Total.*:\*\* \d+/\*\*Total ${ENTRY_TITLE}s:\*\* $TOTAL_COUNT/" "$TARGET_FILE"
fi

# Output
echo -e "${GREEN}✅ Shared $TYPE: $CATEGORY${NC}"
echo -e "${BLUE}   $LEARNING${NC}"
echo -e "${YELLOW}📁 Added to: $(basename $TARGET_FILE)${NC}"
echo -e "${YELLOW}🔍 Search with: ./session-search-knowledge.sh \"keyword\"${NC}"

# Send broadcast message
if [ -f "$SCRIPT_DIR/session-send-message.sh" ]; then
    "$SCRIPT_DIR/session-send-message.sh" broadcast "KNOWLEDGE" "$SESSION_ID: $CATEGORY - $LEARNING" 2>/dev/null || true
fi

exit 0
