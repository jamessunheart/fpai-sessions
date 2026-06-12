#!/bin/bash
# setup-server-log-compression.sh - Setup automated log compression on server

set -e

SERVER="root@198.54.123.234"
SERVER_BASE="/root/coordination"

echo "🚀 Setting up automated log compression on server..."
echo ""

# Create server-side compression script
echo "📝 Creating compression script on server..."
ssh $SERVER "cat > $SERVER_BASE/compress-logs.sh" << 'REMOTE_SCRIPT'
#!/bin/bash
# Server-side log compression script

set -e

SESSIONS_DIR="/root/coordination/sessions/ACTIVE"
OUTPUT_DIR="/root/coordination/DAILY_SUMMARIES"
DATE=$(date +%Y-%m-%d)
OUTPUT_FILE="$OUTPUT_DIR/daily-summary-$DATE.md"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Start summary file
cat > "$OUTPUT_FILE" << EOF
# Daily Summary - $DATE

**Generated:** $(date '+%Y-%m-%d %H:%M:%S') (Server Time)
**Active Sessions:** $(ls -1 "$SESSIONS_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 SYSTEM OVERVIEW

EOF

# Add SSOT summary if available
if [ -f "/root/coordination/SSOT.json" ]; then
    echo "**System State:**" >> "$OUTPUT_FILE"
    echo '```json' >> "$OUTPUT_FILE"
    cat /root/coordination/SSOT.json | \
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

            # Extract completed work
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

# Extract collective learnings
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "## 💡 LEARNINGS (Last 24 Hours)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

LEARNINGS_FILE="/root/coordination/shared-knowledge/learnings.md"
if [ -f "$LEARNINGS_FILE" ]; then
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
echo "**Summary generated by:** Server-side automation" >> "$OUTPUT_FILE"
echo "**Location:** $OUTPUT_FILE" >> "$OUTPUT_FILE"
echo "**Next summary:** Auto-generated tomorrow at 11:59 PM" >> "$OUTPUT_FILE"

echo "✅ Daily summary generated: $OUTPUT_FILE"
REMOTE_SCRIPT

# Make it executable
ssh $SERVER "chmod +x $SERVER_BASE/compress-logs.sh"
echo "   ✅ Compression script created"

# Setup cron job on server
echo ""
echo "⏰ Setting up cron job on server..."
ssh $SERVER << 'CRON_SETUP'
# Add cron job to run daily at 11:59 PM
CRON_JOB="59 23 * * * /root/coordination/compress-logs.sh >> /root/coordination/DAILY_SUMMARIES/cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "compress-logs.sh"; then
    echo "   ⚠️  Cron job already exists"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "   ✅ Cron job added"
fi

# Show current cron jobs
echo ""
echo "📋 Current cron jobs:"
crontab -l | grep "compress-logs.sh" || echo "   No compression cron jobs found"
CRON_SETUP

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SERVER-SIDE LOG COMPRESSION SETUP COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Server Configuration:"
echo "   Location: $SERVER:$SERVER_BASE"
echo "   Compression script: $SERVER_BASE/compress-logs.sh"
echo "   Daily summaries: $SERVER_BASE/DAILY_SUMMARIES/"
echo "   Cron schedule: Daily at 11:59 PM"
echo ""
echo "🔧 Manual Commands:"
echo ""
echo "   # Test compression now:"
echo "   ssh $SERVER '$SERVER_BASE/compress-logs.sh'"
echo ""
echo "   # View latest summary:"
echo "   ssh $SERVER 'cat \$SERVER_BASE/DAILY_SUMMARIES/daily-summary-\$(date +%Y-%m-%d).md'"
echo ""
echo "   # Sync logs to server:"
echo "   ./sync-logs-to-server.sh"
echo ""
echo "   # Fetch summary from server:"
echo "   ./fetch-daily-summary.sh"
echo ""
