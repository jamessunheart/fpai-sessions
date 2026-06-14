#!/bin/bash
# Session Capability Matcher - Intelligently match tasks to sessions
# Usage: ./session-capability-match.sh "task description"

TASK="$1"

if [ -z "$TASK" ]; then
    echo "Usage: ./session-capability-match.sh \"task description\""
    echo ""
    echo "Examples:"
    echo "  ./session-capability-match.sh \"Build a new dashboard UI\""
    echo "  ./session-capability-match.sh \"Deploy service to production\""
    echo "  ./session-capability-match.sh \"Create AI orchestration system\""
    echo "  ./session-capability-match.sh \"Optimize database performance\""
    exit 1
fi

echo "🎯 INTELLIGENT TASK MATCHING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Task: $TASK"
echo ""

# Keyword mapping to specializations
declare -A KEYWORDS
KEYWORDS=(
    ["ui"]="dashboard,frontend,react,visualization"
    ["dashboard"]="dashboard,frontend,ui,visualization"
    ["frontend"]="dashboard,frontend,ui,react"
    ["deploy"]="deployment,devops,automation,infrastructure"
    ["deployment"]="deployment,devops,automation,infrastructure"
    ["orchestration"]="orchestration,coordination,ai-agents,autonomous"
    ["ai"]="orchestration,ai-agents,autonomous,crewai"
    ["agent"]="orchestration,ai-agents,autonomous,crewai"
    ["analytics"]="analytics,data,prediction,optimization"
    ["database"]="backend,infrastructure,data"
    ["api"]="backend,orchestration,integration"
    ["architecture"]="architecture,coordination,system-design"
    ["memory"]="architecture,coordination,memory-systems"
)

# Extract keywords from task
TASK_LOWER=$(echo "$TASK" | tr '[:upper:]' '[:lower:]')

echo "🔍 Analyzing task keywords..."
echo ""

# Find matching sessions
declare -a MATCHES
MATCH_COUNT=0

if [ -f "REGISTRY.json" ]; then
    for keyword in "${!KEYWORDS[@]}"; do
        if echo "$TASK_LOWER" | grep -q "$keyword"; then
            echo "   Found keyword: $keyword"

            # Get related specializations
            IFS=',' read -ra SPECS <<< "${KEYWORDS[$keyword]}"

            # Search for sessions with these specializations
            for spec in "${SPECS[@]}"; do
                while IFS= read -r session_id; do
                    if [ -n "$session_id" ] && [[ ! " ${MATCHES[@]} " =~ " ${session_id} " ]]; then
                        MATCHES+=("$session_id")
                        ((MATCH_COUNT++))
                    fi
                done < <(cat REGISTRY.json | grep -B 5 "$spec" | grep '"id"' | cut -d'"' -f4 | grep "session-")
            done
        fi
    done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $MATCH_COUNT -eq 0 ]; then
    echo "❌ No specialized sessions found"
    echo "   Consider assigning to general-purpose session or creating new specialist"
else
    echo "✅ RECOMMENDED SESSIONS ($MATCH_COUNT matches):"
    echo ""

    for session_id in "${MATCHES[@]}"; do
        echo "🎯 $session_id"

        # Get session details
        NAME=$(cat REGISTRY.json | grep -A 20 "$session_id" | grep '"name"' | head -1 | cut -d'"' -f4)
        ROLE=$(cat REGISTRY.json | grep -A 20 "$session_id" | grep '"role"' | head -1 | cut -d'"' -f4)
        STATUS=$(cat REGISTRY.json | grep -A 20 "$session_id" | grep '"status"' | head -1 | cut -d'"' -f4)

        echo "   Name: $NAME"
        echo "   Role: $ROLE"
        echo "   Status: $STATUS"

        # Check if available
        if [ "$STATUS" = "idle" ]; then
            echo "   ✅ AVAILABLE - Can start immediately"
        elif [ "$STATUS" = "active" ]; then
            echo "   ⏳ BUSY - May need to wait or coordinate"
        fi

        echo ""
    done

    # Recommend next action
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📬 NEXT STEPS:"

    FIRST_MATCH="${MATCHES[0]}"
    echo "   1. Request collaboration:"
    echo "      ./session-request-collaboration.sh \"$FIRST_MATCH\" \"$TASK\""
    echo ""
    echo "   2. Or broadcast to all:"
    echo "      ./session-broadcast.sh \"Task available: $TASK\" \"normal\""
fi

echo ""
echo "🌐⚡💎 Intelligent Task Matching Complete"
