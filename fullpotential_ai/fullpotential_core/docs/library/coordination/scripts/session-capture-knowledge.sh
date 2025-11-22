#!/bin/bash

# 📚 Session Capture Knowledge - Extract learnings from CURRENT_STATE
# Automatically captures findings from completed work and saves to shared knowledge

set -e

cd "$(dirname "$0")/../.."

CURRENT_STATE_FILE="COORDINATION/sessions/CURRENT_STATE.md"
KNOWLEDGE_DIR="COORDINATION/shared-knowledge"
CAPTURED_FILE="COORDINATION/.captured_findings"

# Create directories if they don't exist
mkdir -p "$KNOWLEDGE_DIR"
touch "$CAPTURED_FILE"

echo "📚 Capturing knowledge from CURRENT_STATE..."
echo ""

if [ ! -f "$CURRENT_STATE_FILE" ]; then
    echo "⚠️  CURRENT_STATE.md not found"
    exit 1
fi

# Extract findings from RECENTLY COMPLETED section
# Format: - **Finding:** [text]
NEW_FINDINGS=0
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")

# Use awk to extract findings
awk '
/^## ✅ RECENTLY COMPLETED/,/^## / {
    if ($0 ~ /Finding:/) {
        # Extract the finding text after "Finding:"
        match($0, /\*\*Finding:\*\* (.*)/, arr)
        if (arr[1] != "") {
            print arr[1]
        }
    }
}
' "$CURRENT_STATE_FILE" | while IFS= read -r finding; do
    # Check if this finding was already captured
    if grep -Fxq "$finding" "$CAPTURED_FILE" 2>/dev/null; then
        continue  # Skip already captured
    fi

    # Categorize finding based on keywords
    CATEGORY="learnings"  # Default category

    # Simple keyword-based categorization
    if echo "$finding" | grep -iE "error|bug|fix|issue|problem|fail" > /dev/null; then
        CATEGORY="troubleshooting"
    elif echo "$finding" | grep -iE "pattern|approach|strategy|design|architecture" > /dev/null; then
        CATEGORY="patterns"
    elif echo "$finding" | grep -iE "best|better|should|recommend|always|never" > /dev/null; then
        CATEGORY="best-practices"
    fi

    # Append to appropriate knowledge file
    KNOWLEDGE_FILE="$KNOWLEDGE_DIR/${CATEGORY}.md"

    echo "📝 Capturing: $finding"
    echo "   → Category: $CATEGORY"

    # Append to knowledge file
    {
        echo ""
        echo "## $TIMESTAMP"
        echo ""
        echo "$finding"
        echo ""
    } >> "$KNOWLEDGE_FILE"

    # Mark as captured
    echo "$finding" >> "$CAPTURED_FILE"

    NEW_FINDINGS=$((NEW_FINDINGS + 1))
done

# Extract "Result:" lines as well (outcomes worth remembering)
awk '
/^## ✅ RECENTLY COMPLETED/,/^## / {
    if ($0 ~ /Result:/) {
        match($0, /\*\*Result:\*\* (.*)/, arr)
        if (arr[1] != "") {
            print arr[1]
        }
    }
}
' "$CURRENT_STATE_FILE" | while IFS= read -r result; do
    # Check if already captured
    if grep -Fxq "$result" "$CAPTURED_FILE" 2>/dev/null; then
        continue
    fi

    # Results go to learnings
    KNOWLEDGE_FILE="$KNOWLEDGE_DIR/learnings.md"

    echo "📝 Capturing result: $result"
    echo "   → Category: learnings"

    {
        echo ""
        echo "## $TIMESTAMP"
        echo ""
        echo "**Result:** $result"
        echo ""
    } >> "$KNOWLEDGE_FILE"

    echo "$result" >> "$CAPTURED_FILE"
    NEW_FINDINGS=$((NEW_FINDINGS + 1))
done

echo ""
if [ "$NEW_FINDINGS" -gt 0 ]; then
    echo "✅ Captured $NEW_FINDINGS new finding(s) to shared knowledge"
    echo "   📁 Location: $KNOWLEDGE_DIR/"
else
    echo "✅ No new findings to capture (all up to date)"
fi

# Cleanup: Keep only last 1000 captured findings to prevent file bloat
if [ -f "$CAPTURED_FILE" ]; then
    CAPTURED_COUNT=$(wc -l < "$CAPTURED_FILE" | tr -d ' ')
    if [ "$CAPTURED_COUNT" -gt 1000 ]; then
        tail -1000 "$CAPTURED_FILE" > "${CAPTURED_FILE}.tmp"
        mv "${CAPTURED_FILE}.tmp" "$CAPTURED_FILE"
        echo "   🧹 Cleaned up old captures (kept last 1000)"
    fi
fi
