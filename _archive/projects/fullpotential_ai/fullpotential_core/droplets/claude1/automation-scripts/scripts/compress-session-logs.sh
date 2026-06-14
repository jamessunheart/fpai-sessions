#!/bin/bash
# compress-session-logs.sh - Generate daily summary from all session logs

set -e

SESSIONS_DIR="/Users/jamessunheart/Development/docs/coordination/sessions/ACTIVE"
OUTPUT_DIR="/Users/jamessunheart/Development/docs/coordination/DAILY_SUMMARIES"
DATE=$(date +%Y-%m-%d)
OUTPUT_FILE="$OUTPUT_DIR/daily-summary-$DATE.md"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Start summary file
cat > "$OUTPUT_FILE" << EOF
# Daily Summary - $DATE

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Active Sessions:** $(ls -1 "$SESSIONS_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 SYSTEM OVERVIEW

EOF

# Add SSOT summary if available
if [ -f "/Users/jamessunheart/Development/docs/coordination/SSOT.json" ]; then
    echo "**System State:**" >> "$OUTPUT_FILE"
    echo '```json' >> "$OUTPUT_FILE"
    cat /Users/jamessunheart/Development/docs/coordination/SSOT.json | \
        python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps({k:v for k,v in data.items() if k in ['session_count', 'server_status']}, indent=2))" \
        >> "$OUTPUT_FILE" 2>/dev/null || echo "SSOT data unavailable" >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "## 📊 SESSION ACTIVITY" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Process each active session log
if ls "$SESSIONS_DIR"/*.md >/dev/null 2>&1; then
    for log_file in "$SESSIONS_DIR"/*.md; do
        if [ -f "$log_file" ]; then
            session_name=$(basename "$log_file" .md)

            echo "### $session_name" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"

            # Extract metadata
            role=$(grep "^\*\*Role:\*\*" "$log_file" | head -1 | sed 's/\*\*Role:\*\* //' || echo "Unknown")
            goal=$(grep "^\*\*Goal:\*\*" "$log_file" | head -1 | sed 's/\*\*Goal:\*\* //' || echo "Unknown")
            status=$(grep "^\*\*Status:\*\*" "$log_file" | head -1 | sed 's/\*\*Status:\*\* //' || echo "Unknown")

            echo "**Role:** $role" >> "$OUTPUT_FILE"
            echo "**Goal:** $goal" >> "$OUTPUT_FILE"
            echo "**Status:** $status" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"

            # Extract current work
            echo "**Current Work:**" >> "$OUTPUT_FILE"
            awk '/^## Current Work/,/^## [A-Z]/' "$log_file" | \
                grep -v "^## Current Work" | \
                grep -v "^## [A-Z]" | \
                head -10 | \
                sed 's/^/  /' >> "$OUTPUT_FILE" || echo "  No current work documented" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"

            # Extract today's completed work
            echo "**Completed Today:**" >> "$OUTPUT_FILE"
            awk "/\*\*$DATE:\*\*/,/\*\*[0-9]/" "$log_file" | \
                grep "^- \[x\]" | \
                head -5 | \
                sed 's/^/  /' >> "$OUTPUT_FILE" 2>/dev/null || echo "  No completed tasks today" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"

            # Extract blockers
            blockers=$(awk '/^## Blockers & Issues/,/^## [A-Z]/' "$log_file" | \
                grep "^- \[ \]" | \
                head -3)

            if [ ! -z "$blockers" ]; then
                echo "**Blockers:**" >> "$OUTPUT_FILE"
                echo "$blockers" | sed 's/^/  /' >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
            fi

            echo "---" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
        fi
    done
else
    echo "No active session logs found." >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# Extract collective learnings from today
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "## 💡 LEARNINGS (Last 24 Hours)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

LEARNINGS_FILE="/Users/jamessunheart/Development/docs/coordination/shared-knowledge/learnings.md"
if [ -f "$LEARNINGS_FILE" ]; then
    # Get learnings from today
    grep -A 10 "^### $DATE" "$LEARNINGS_FILE" | head -15 >> "$OUTPUT_FILE" 2>/dev/null || echo "No new learnings today" >> "$OUTPUT_FILE"
else
    echo "No learnings file found" >> "$OUTPUT_FILE"
fi

echo "" >> "$OUTPUT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "## 📈 METRICS" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Calculate metrics
total_sessions=$(ls -1 "$SESSIONS_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
total_blockers=$(grep -h "^- \[ \]" "$SESSIONS_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
total_completed=$(grep -h "^- \[x\].*$DATE" "$SESSIONS_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')

echo "- **Active Sessions:** $total_sessions" >> "$OUTPUT_FILE"
echo "- **Tasks Completed Today:** $total_completed" >> "$OUTPUT_FILE"
echo "- **Current Blockers:** $total_blockers" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "**Summary generated by:** compress-session-logs.sh" >> "$OUTPUT_FILE"
echo "**Next summary:** Run ./compress-session-logs.sh tomorrow" >> "$OUTPUT_FILE"

# Print success message
echo "✅ Daily summary created: $OUTPUT_FILE"
echo ""
echo "📊 Summary Statistics:"
echo "   - Active Sessions: $total_sessions"
echo "   - Completed Tasks: $total_completed"
echo "   - Current Blockers: $total_blockers"
echo ""
echo "📖 View summary:"
echo "   cat $OUTPUT_FILE"
echo ""
echo "📁 All summaries:"
echo "   ls -lh $OUTPUT_DIR/"
