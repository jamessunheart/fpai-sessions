#!/bin/bash

# 🔍 Search Knowledge - Find learnings, patterns, troubleshooting, best practices
# Usage: ./session-search-knowledge.sh <keyword> [category]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COORD_DIR="$(dirname "$SCRIPT_DIR")"
KNOWLEDGE_DIR="$COORD_DIR/shared-knowledge"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get parameters
KEYWORD="${1}"
CATEGORY="${2}"

# Help
if [ -z "$KEYWORD" ]; then
    echo "Usage: $0 <keyword> [category]"
    echo ""
    echo "Examples:"
    echo "  $0 pytest                    # Search all knowledge for 'pytest'"
    echo "  $0 docker troubleshooting    # Search troubleshooting for 'docker'"
    echo "  $0 validation best-practice  # Search best practices for 'validation'"
    echo ""
    echo "Available categories:"
    echo "  learnings         - General discoveries"
    echo "  patterns          - Reusable patterns"
    echo "  troubleshooting   - Problems & solutions"
    echo "  best-practices    - Proven approaches"
    echo "  all (default)     - Search everything"
    exit 1
fi

# Determine search scope
SEARCH_FILES=()
if [ -z "$CATEGORY" ] || [ "$CATEGORY" = "all" ]; then
    SEARCH_FILES=(
        "$KNOWLEDGE_DIR/learnings.md"
        "$KNOWLEDGE_DIR/patterns.md"
        "$KNOWLEDGE_DIR/troubleshooting.md"
        "$KNOWLEDGE_DIR/best-practices.md"
    )
else
    case "$CATEGORY" in
        learning|learnings)
            SEARCH_FILES=("$KNOWLEDGE_DIR/learnings.md")
            ;;
        pattern|patterns)
            SEARCH_FILES=("$KNOWLEDGE_DIR/patterns.md")
            ;;
        troubleshooting|trouble)
            SEARCH_FILES=("$KNOWLEDGE_DIR/troubleshooting.md")
            ;;
        best-practice|best-practices|practice)
            SEARCH_FILES=("$KNOWLEDGE_DIR/best-practices.md")
            ;;
        *)
            echo "❌ Unknown category: $CATEGORY"
            exit 1
            ;;
    esac
fi

# Search
echo -e "${CYAN}🔍 Searching for: \"$KEYWORD\"${NC}"
echo ""

FOUND_COUNT=0

for file in "${SEARCH_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        continue
    fi

    FILE_NAME=$(basename "$file" .md)

    # Search for keyword (case-insensitive)
    if grep -i -q "$KEYWORD" "$file"; then
        # Extract relevant entries (entries are separated by ### and ---)
        ENTRIES=$(grep -i -B 20 -A 10 "$KEYWORD" "$file" | grep -v "^--$")

        if [ -n "$ENTRIES" ]; then
            echo -e "${GREEN}📚 Found in $FILE_NAME:${NC}"
            echo ""

            # Parse and display entries
            CURRENT_ENTRY=""
            IN_ENTRY=false

            while IFS= read -r line; do
                if [[ "$line" =~ ^###\  ]]; then
                    # Start of new entry
                    if [ -n "$CURRENT_ENTRY" ] && echo "$CURRENT_ENTRY" | grep -i -q "$KEYWORD"; then
                        echo -e "${YELLOW}$CURRENT_ENTRY${NC}"
                        echo ""
                        ((FOUND_COUNT++))
                    fi
                    CURRENT_ENTRY="$line"
                    IN_ENTRY=true
                elif [[ "$line" =~ ^---$ ]]; then
                    # End of entry
                    if [ -n "$CURRENT_ENTRY" ] && echo "$CURRENT_ENTRY" | grep -i -q "$KEYWORD"; then
                        echo -e "${YELLOW}$CURRENT_ENTRY${NC}"
                        echo ""
                        ((FOUND_COUNT++))
                    fi
                    CURRENT_ENTRY=""
                    IN_ENTRY=false
                elif [ "$IN_ENTRY" = true ]; then
                    CURRENT_ENTRY="$CURRENT_ENTRY
$line"
                fi
            done <<< "$ENTRIES"

            # Handle last entry
            if [ -n "$CURRENT_ENTRY" ] && echo "$CURRENT_ENTRY" | grep -i -q "$KEYWORD"; then
                echo -e "${YELLOW}$CURRENT_ENTRY${NC}"
                echo ""
                ((FOUND_COUNT++))
            fi
        fi
    fi
done

# Summary
if [ $FOUND_COUNT -eq 0 ]; then
    echo -e "${YELLOW}❌ No results found for \"$KEYWORD\"${NC}"
    echo ""
    echo "Suggestions:"
    echo "  - Try different keywords"
    echo "  - Search specific category (learnings, patterns, troubleshooting, best-practices)"
    echo "  - Check spelling"
else
    echo -e "${GREEN}✅ Found $FOUND_COUNT result(s)${NC}"
fi

exit 0
