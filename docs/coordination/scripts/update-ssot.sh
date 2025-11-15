#!/bin/bash

# Update Single Source of Truth
# This script updates SSOT.json with current, accurate system state

COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
SSOT_FILE="$COORDINATION_DIR/SSOT.json"

# Count actual Claude processes
TOTAL_PROCESSES=$(ps aux | grep -E "^\S+\s+\d+.*claude$" | grep -v grep | wc -l | tr -d ' ')

# Get terminals
TERMINALS=$(ps aux | grep -E "^\S+\s+\d+.*claude$" | grep -v grep | awk '{print $7}' | sort -u | tr '\n' ',' | sed 's/,$//')

# Count registered sessions
REGISTERED=$(ls -1 "$COORDINATION_DIR/sessions"/*.json 2>/dev/null | wc -l | tr -d ' ')

# Calculate unregistered
UNREGISTERED=$((TOTAL_PROCESSES - REGISTERED))

# Count active (>10% CPU)
ACTIVE=$(ps aux | grep -E "^\S+\s+\d+.*claude$" | grep -v grep | awk '$3 > 10' | wc -l | tr -d ' ')

# Count idle
IDLE=$((TOTAL_PROCESSES - ACTIVE))

# Git changes
GIT_CHANGES=$(cd /Users/jamessunheart/Development && git status --short 2>/dev/null | wc -l | tr -d ' ')

# Check servers
check_server() {
    local port=$1
    curl -s --connect-timeout 1 "http://198.54.123.234:$port/health" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "online"
    else
        echo "offline"
    fi
}

SERVER_8000=$(check_server 8000)
SERVER_8001=$(check_server 8001)
SERVER_8002=$(check_server 8002)
SERVER_8009=$(check_server 8009)
SERVER_8010=$(check_server 8010)
SERVER_8025=$(check_server 8025)

# Check dashboard status
SIMPLE_STATUS="unknown"
VISUAL_STATUS="unknown"

if lsof -ti:8030 > /dev/null 2>&1; then
    SIMPLE_STATUS="running"
else
    SIMPLE_STATUS="stopped"
fi

if lsof -ti:8031 > /dev/null 2>&1; then
    VISUAL_STATUS="running"
else
    VISUAL_STATUS="stopped"
fi

# Generate SSOT JSON
cat > "$SSOT_FILE" << EOF
{
  "last_update": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "session_count": {
    "total_processes": $TOTAL_PROCESSES,
    "registered": $REGISTERED,
    "unregistered": $UNREGISTERED,
    "active": $ACTIVE,
    "idle": $IDLE
  },
  "terminals": [$(echo "$TERMINALS" | sed 's/,/", "/g' | sed 's/^/"/' | sed 's/$/"/')],
  "server_status": {
    "8000": "$SERVER_8000",
    "8001": "$SERVER_8001",
    "8002": "$SERVER_8002",
    "8009": "$SERVER_8009",
    "8010": "$SERVER_8010",
    "8025": "$SERVER_8025"
  },
  "dashboards": {
    "simple": {
      "port": 8030,
      "status": "$SIMPLE_STATUS",
      "url": "http://localhost:8030"
    },
    "visual": {
      "port": 8031,
      "status": "$VISUAL_STATUS",
      "url": "http://localhost:8031"
    }
  },
  "git_changes": $GIT_CHANGES,
  "metadata": {
    "description": "Single Source of Truth for Claude Code Multi-Session Coordination",
    "update_frequency": "Every 5 seconds",
    "primary_source": true,
    "verified": true
  }
}
EOF

echo "✅ SSOT updated: $TOTAL_PROCESSES total, $REGISTERED registered, $ACTIVE active"
