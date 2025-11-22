#!/bin/bash

# 📊 PRIORITY CALCULATOR - Score work items
# Uses formula: Priority = Impact × Alignment × Unblocked

set -e

cd "$(dirname "$0")/../.."

echo "📊 Priority Calculator"
echo "====================="
echo ""
echo "Formula: Priority = Impact × Alignment × Unblocked"
echo ""

# Define work items with scores
# Format: "name:impact:alignment:unblocked:description"
WORK_ITEMS=(
    "orchestrator_restart:8:8:10:Restart Orchestrator service (currently offline)"
    "dashboard_deploy:7:9:3:Deploy dashboard fix (requires SSH)"
    "spec_generation:6:8:10:Generate SPEC.md for services"
    "ad_campaign:10:10:5:Launch $100 ad campaign (needs DNS)"
    "unified_registry:8:10:10:Create unified work registry"
    "consciousness_loop:9:10:10:Build automated consciousness loop"
)

echo "📋 Work Items Scored:"
echo ""

# Calculate priorities and store for sorting
PRIORITIES_FILE="/tmp/priorities_$$"
> "$PRIORITIES_FILE"

for item in "${WORK_ITEMS[@]}"; do
    IFS=':' read -r name impact alignment unblocked description <<< "$item"

    # Calculate priority score
    priority=$((impact * alignment * unblocked / 100))

    printf "%-25s | Impact: %2d | Align: %2d | Unblock: %2d | Score: %3d\n" \
        "$name" "$impact" "$alignment" "$unblocked" "$priority"
    echo "   → $description"
    echo ""

    # Store for sorting
    echo "$priority:$name:$description" >> "$PRIORITIES_FILE"
done

# Sort and display top priorities
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Top Priorities (Sorted by Score):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sort -t: -k1 -nr "$PRIORITIES_FILE" | while IFS=: read -r score name description; do
    echo "🏆 Score: $score - $name"
    echo "   $description"
    echo ""
done

# Return highest priority work as output
HIGHEST=$(sort -t: -k1 -nr "$PRIORITIES_FILE" | head -1)
HIGHEST_SCORE=$(echo "$HIGHEST" | cut -d: -f1)
HIGHEST_NAME=$(echo "$HIGHEST" | cut -d: -f2)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Highest Priority: $HIGHEST_NAME (Score: $HIGHEST_SCORE)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Cleanup
rm -f "$PRIORITIES_FILE"
