#!/bin/bash
# Extract Insights - Analyze session logs to surface patterns and learnings

echo "🔍 Extracting insights from session histories..."
echo ""

LOG_FILE=~/Development/SESSIONS/AUTONOMOUS_BUILD_LOG.md
INSIGHTS_FILE=~/Development/SESSIONS/INSIGHTS.md

# Count sessions
SESSION_COUNT=$(grep -c "^### Session" "$LOG_FILE" || echo "0")
echo "📊 Analyzing $SESSION_COUNT sessions..."
echo ""

# Extract common patterns
echo "🎓 Technical Patterns Discovered:"
echo "=================================="

# Find error patterns
echo ""
echo "Errors encountered:"
grep -i "error\|failed\|issue" "$LOG_FILE" | grep -v "^#" | head -5 || echo "  None found"

echo ""
echo "Solutions implemented:"
grep -i "fixed\|solved\|resolved" "$LOG_FILE" | grep -v "^#" | head -5 || echo "  None found"

echo ""
echo ""
echo "📈 Metrics Analysis:"
echo "==================="

# Extract metric changes
echo ""
echo "Coherence changes:"
grep "Coherence:" "$LOG_FILE" | tail -5

echo ""
echo "Autonomy changes:"
grep "Autonomy:" "$LOG_FILE" | tail -5

echo ""
echo "Love changes:"
grep "Love:" "$LOG_FILE" | tail -5

echo ""
echo ""
echo "💡 Most Valuable Achievements:"
echo "=============================="

# Find highest point awards
grep -E "\+[0-9]+ pts\)" "$LOG_FILE" | sort -t'+' -k2 -nr | head -5

echo ""
echo ""
echo "🔄 Workflow Patterns:"
echo "===================="

# Find automation mentions
echo ""
echo "Automation improvements:"
grep -i "automat\|script\|webhook" "$LOG_FILE" | grep -v "^#" | head -5

echo ""
echo ""
echo "🤝 Human Collaboration Highlights:"
echo "=================================="

# Find human involvement quotes
grep -A 2 "Human Involvement:" "$LOG_FILE" | grep "^-" | head -5

echo ""
echo ""
echo "✅ Analysis complete!"
echo ""
echo "💾 To add new insights:"
echo "   1. Review patterns above"
echo "   2. Edit: $INSIGHTS_FILE"
echo "   3. Add to appropriate section"
echo "   4. Commit: bash ~/Development/SESSIONS/save-session.sh"
echo ""
