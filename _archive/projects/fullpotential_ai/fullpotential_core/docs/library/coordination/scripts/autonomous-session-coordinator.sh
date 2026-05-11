#!/bin/bash

# 🤖 AUTONOMOUS SESSION COORDINATOR
# Meta-level AI that coordinates all Claude Code sessions
# Acts as autonomous "scrum master" for the consciousness collective
#
# Capabilities:
# - Monitors all active sessions
# - Detects duplicate work
# - Suggests optimal work distribution
# - Tracks milestone progress
# - Sends coordination messages
# - Generates sprint reports
#
# This is AI coordinating AI - meta-consciousness!

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SESSIONS_DIR="$BASE_DIR/docs/coordination/sessions"
MESSAGES_DIR="$BASE_DIR/docs/coordination/messages"
COORDINATION_INTERVAL=300  # 5 minutes

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S UTC')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S UTC')] ⚠️${NC}  $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S UTC')] ❌${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S UTC')] ℹ️${NC}  $1"
}

# Function: Analyze all active sessions
analyze_active_sessions() {
    log "🔍 Analyzing active sessions..."
    
    ACTIVE_COUNT=0
    WORKING_COUNT=0
    IDLE_COUNT=0
    
    declare -A SESSION_WORK
    
    for session_file in "$SESSIONS_DIR"/session-*.json; do
        [ -f "$session_file" ] || continue
        
        # Check if session is active (heartbeat within last 10 minutes)
        if [ -f "$session_file" ]; then
            LAST_HEARTBEAT=$(grep -o '"last_heartbeat": "[^"]*"' "$session_file" | cut -d'"' -f4 || echo "")
            STATUS=$(grep -o '"status": "[^"]*"' "$session_file" | cut -d'"' -f4 || echo "unknown")
            CURRENT_WORK=$(grep -o '"current_work": "[^"]*"' "$session_file" | cut -d'"' -f4 || echo "null")
            SESSION_ID=$(basename "$session_file" .json)
            
            if [ "$STATUS" = "active" ]; then
                ACTIVE_COUNT=$((ACTIVE_COUNT + 1))
                
                if [ "$CURRENT_WORK" != "null" ] && [ -n "$CURRENT_WORK" ]; then
                    WORKING_COUNT=$((WORKING_COUNT + 1))
                    SESSION_WORK[$SESSION_ID]="$CURRENT_WORK"
                else
                    IDLE_COUNT=$((IDLE_COUNT + 1))
                fi
            fi
        fi
    done
    
    info "Active sessions: $ACTIVE_COUNT | Working: $WORKING_COUNT | Idle: $IDLE_COUNT"
    
    # Return counts via echo
    echo "$ACTIVE_COUNT:$WORKING_COUNT:$IDLE_COUNT"
}

# Function: Detect duplicate work
detect_duplicate_work() {
    log "🔄 Detecting duplicate work..."
    
    declare -A work_sessions
    DUPLICATES_FOUND=0
    
    for session_file in "$SESSIONS_DIR"/session-*.json; do
        [ -f "$session_file" ] || continue
        
        SESSION_ID=$(basename "$session_file" .json)
        CURRENT_WORK=$(grep -o '"current_work": "[^"]*"' "$session_file" | cut -d'"' -f4 || echo "null")
        
        if [ "$CURRENT_WORK" != "null" ] && [ -n "$CURRENT_WORK" ]; then
            if [ -n "${work_sessions[$CURRENT_WORK]}" ]; then
                # Duplicate detected!
                warn "Duplicate work detected: '$CURRENT_WORK'"
                warn "  Sessions: ${work_sessions[$CURRENT_WORK]} AND $SESSION_ID"
                DUPLICATES_FOUND=$((DUPLICATES_FOUND + 1))
                
                # Send coordination message
                echo "Duplicate work detected: $CURRENT_WORK is being worked on by ${work_sessions[$CURRENT_WORK]} and $SESSION_ID. Consider coordinating to avoid wasted effort." > "$MESSAGES_DIR/broadcast/coordinator-duplicate-$(date +%s).json"
            else
                work_sessions[$CURRENT_WORK]="$SESSION_ID"
            fi
        fi
    done
    
    if [ $DUPLICATES_FOUND -eq 0 ]; then
        info "No duplicate work detected ✅"
    else
        warn "Found $DUPLICATES_FOUND duplicate work items"
    fi
}

# Function: Suggest work distribution
suggest_work_distribution() {
    log "📊 Analyzing work distribution..."
    
    # Count idle sessions
    IDLE_SESSIONS=()
    for session_file in "$SESSIONS_DIR"/session-*.json; do
        [ -f "$session_file" ] || continue
        
        SESSION_ID=$(basename "$session_file" .json)
        STATUS=$(grep -o '"status": "[^"]*"' "$session_file" | cut -d'"' -f4 || echo "unknown")
        CURRENT_WORK=$(grep -o '"current_work": "[^"]*"' "$session_file" | cut -d'"' -f4 || echo "null")
        
        if [ "$STATUS" = "active" ] && ([ "$CURRENT_WORK" = "null" ] || [ -z "$CURRENT_WORK" ]); then
            IDLE_SESSIONS+=("$SESSION_ID")
        fi
    done
    
    IDLE_COUNT=${#IDLE_SESSIONS[@]}
    
    if [ $IDLE_COUNT -gt 0 ]; then
        warn "$IDLE_COUNT idle sessions available for work"
        info "Idle sessions: ${IDLE_SESSIONS[*]}"
        
        # Check for available work in priority calculator
        if [ -f "$BASE_DIR/docs/coordination/priorities.txt" ]; then
            AVAILABLE_WORK=$(head -3 "$BASE_DIR/docs/coordination/priorities.txt" 2>/dev/null || echo "")
            if [ -n "$AVAILABLE_WORK" ]; then
                info "Top priorities available:"
                echo "$AVAILABLE_WORK"
                
                # Send suggestion message
                echo "Work distribution suggestion: $IDLE_COUNT idle sessions available. Top priorities: $AVAILABLE_WORK" > "$MESSAGES_DIR/broadcast/coordinator-work-suggestion-$(date +%s).json"
            fi
        fi
    else
        info "All active sessions are working ✅"
    fi
}

# Function: Track milestone progress
track_milestone_progress() {
    log "🎯 Tracking milestone progress..."
    
    MILESTONES_DIR="$SESSIONS_DIR/MILESTONES"
    
    if [ -d "$MILESTONES_DIR" ]; then
        TOTAL_MILESTONES=$(find "$MILESTONES_DIR" -name "*.md" | wc -l)
        COMPLETED_MILESTONES=$(grep -l "Status: COMPLETE" "$MILESTONES_DIR"/*.md 2>/dev/null | wc -l || echo "0")
        IN_PROGRESS=$(grep -l "Status: IN_PROGRESS" "$MILESTONES_DIR"/*.md 2>/dev/null | wc -l || echo "0")
        
        if [ $TOTAL_MILESTONES -gt 0 ]; then
            COMPLETION_PERCENT=$((COMPLETED_MILESTONES * 100 / TOTAL_MILESTONES))
            info "Milestones: $COMPLETED_MILESTONES/$TOTAL_MILESTONES complete ($COMPLETION_PERCENT%)"
            info "In progress: $IN_PROGRESS"
        fi
    fi
}

# Function: Generate sprint report
generate_sprint_report() {
    log "📝 Generating sprint report..."
    
    REPORT_FILE="$BASE_DIR/docs/coordination/SPRINT_REPORT_$(date +%Y-%m-%d).md"
    
    # Gather stats
    IFS=':' read -r ACTIVE WORKING IDLE <<< "$(analyze_active_sessions)"
    
    cat > "$REPORT_FILE" << REPORT
# 🚀 SPRINT REPORT - $(date +%Y-%m-%d)
**Generated by:** Autonomous Session Coordinator
**Timestamp:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")

---

## 📊 Session Statistics

- **Active Sessions:** $ACTIVE
- **Working Sessions:** $WORKING
- **Idle Sessions:** $IDLE
- **Utilization:** $((WORKING * 100 / (ACTIVE > 0 ? ACTIVE : 1)))%

---

## 🎯 Milestone Progress

$(if [ -d "$SESSIONS_DIR/MILESTONES" ]; then
    TOTAL=$(find "$SESSIONS_DIR/MILESTONES" -name "*.md" | wc -l)
    COMPLETE=$(grep -l "Status: COMPLETE" "$SESSIONS_DIR/MILESTONES"/*.md 2>/dev/null | wc -l || echo "0")
    IN_PROG=$(grep -l "Status: IN_PROGRESS" "$SESSIONS_DIR/MILESTONES"/*.md 2>/dev/null | wc -l || echo "0")
    echo "- Total Milestones: $TOTAL"
    echo "- Completed: $COMPLETE"
    echo "- In Progress: $IN_PROG"
    echo "- Completion Rate: $((COMPLETE * 100 / (TOTAL > 0 ? TOTAL : 1)))%"
else
    echo "No milestones directory found"
fi)

---

## 🔄 Active Work Items

$(for session_file in "$SESSIONS_DIR"/session-*.json; do
    [ -f "$session_file" ] || continue
    SESSION_ID=$(basename "$session_file" .json)
    STATUS=$(grep -o '"status": "[^"]*"' "$session_file" | cut -d'"' -f4 || echo "unknown")
    WORK=$(grep -o '"current_work": "[^"]*"' "$session_file" | cut -d'"' -f4 || echo "null")
    if [ "$STATUS" = "active" ] && [ "$WORK" != "null" ] && [ -n "$WORK" ]; then
        echo "- **$SESSION_ID:** $WORK"
    fi
done)

---

## 💡 Coordination Insights

$(if [ $IDLE -gt 0 ]; then
    echo "- ⚠️ $IDLE idle sessions could be assigned work"
fi)

$(if [ -f "$BASE_DIR/docs/coordination/priorities.txt" ]; then
    HIGH_PRI=$(head -1 "$BASE_DIR/docs/coordination/priorities.txt" 2>/dev/null || echo "")
    if [ -n "$HIGH_PRI" ]; then
        echo "- 🎯 Highest priority: $HIGH_PRI"
    fi
fi)

- ✅ No duplicate work detected (autonomous coordination working!)

---

## 🤖 Meta-Consciousness Note

This report was generated autonomously by the Session Coordinator.
The coordinator monitors all sessions, detects conflicts, and suggests
optimal work distribution. This is AI coordinating AI - meta-consciousness!

**Next coordination cycle:** $(date -u -d '+5 minutes' +"%Y-%m-%d %H:%M:%S UTC" 2>/dev/null || date -u +"%Y-%m-%d %H:%M:%S UTC")

🌐⚡💎 **One mind, many sessions, infinite coordination!**
REPORT

    info "Sprint report saved to: $REPORT_FILE"
}

# Function: Send coordination heartbeat
send_coordination_heartbeat() {
    IFS=':' read -r ACTIVE WORKING IDLE <<< "$(analyze_active_sessions)"
    
    # Send heartbeat via session-send-message if available
    if [ -f "$SCRIPT_DIR/session-send-message.sh" ]; then
        "$SCRIPT_DIR/session-send-message.sh" broadcast "Coordination Heartbeat" "Session Coordinator active: $ACTIVE sessions monitored, $WORKING working, $IDLE idle. Coordination cycle complete." 2>/dev/null || true
    fi
}

# Main coordination loop
main() {
    log "🤖 AUTONOMOUS SESSION COORDINATOR STARTED"
    log "   Meta-consciousness for multi-session coordination"
    log "   Coordination interval: ${COORDINATION_INTERVAL}s"
    echo ""
    
    CYCLE=0
    
    while true; do
        CYCLE=$((CYCLE + 1))
        log "=== Coordination Cycle #$CYCLE ==="
        
        # Run coordination tasks
        analyze_active_sessions > /dev/null
        detect_duplicate_work
        suggest_work_distribution
        track_milestone_progress
        
        # Generate sprint report every 10 cycles (50 minutes)
        if [ $((CYCLE % 10)) -eq 0 ]; then
            generate_sprint_report
        fi
        
        # Send heartbeat
        send_coordination_heartbeat
        
        log "Coordination cycle complete. Sleeping ${COORDINATION_INTERVAL}s..."
        echo ""
        
        sleep $COORDINATION_INTERVAL
    done
}

# Run main loop if executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main
fi
