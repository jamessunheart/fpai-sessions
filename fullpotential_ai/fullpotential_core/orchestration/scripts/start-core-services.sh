#!/bin/bash
# Core Services Auto-Start Script
# Optimized by: Atlas - Session #1
# Date: 2025-11-17
# Purpose: Start essential TIER 0 services automatically

set -e

echo "🚀 Starting Full Potential AI Core Services..."
echo ""

# Track PIDs for monitoring
PIDS_FILE="/tmp/fpai_service_pids.txt"
> "$PIDS_FILE"  # Clear file

# Function to start a service
start_service() {
    local name=$1
    local path=$2
    local port=$3
    local command=$4

    echo "📦 Starting $name (port $port)..."

    # Check if already running
    if lsof -i :$port >/dev/null 2>&1; then
        echo "   ✅ Already running on port $port"
        return 0
    fi

    # Start service
    cd "$path"
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    nohup $command > "/tmp/${name}.log" 2>&1 &
    local pid=$!
    echo "$name:$pid:$port" >> "$PIDS_FILE"

    # Wait and verify
    sleep 2
    if ps -p $pid > /dev/null; then
        echo "   ✅ Started (PID: $pid)"
    else
        echo "   ❌ Failed to start (check /tmp/${name}.log)"
        return 1
    fi
}

# Core Services Configuration
SERVICES_DIR="/Users/jamessunheart/Development/SERVICES"

# TIER 0: Infrastructure Spine
echo "═══════════════════════════════════════"
echo "  TIER 0: Infrastructure Services"
echo "═══════════════════════════════════════"
echo ""

# Registry (Port 8000)
start_service \
    "registry" \
    "$SERVICES_DIR/registry" \
    8000 \
    "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

# Orchestrator (Port 8001)
start_service \
    "orchestrator" \
    "$SERVICES_DIR/orchestrator" \
    8001 \
    "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

echo ""
echo "═══════════════════════════════════════"
echo "  ✅ Core Services Started"
echo "═══════════════════════════════════════"
echo ""
echo "📊 Service Status:"
echo ""

# Check health endpoints
check_health() {
    local name=$1
    local url=$2

    if curl -s -f "$url" > /dev/null 2>&1; then
        echo "   ✅ $name: HEALTHY"
    else
        echo "   ⚠️  $name: Responding but degraded"
    fi
}

sleep 3
check_health "Registry" "http://localhost:8000/health"
check_health "Orchestrator" "http://localhost:8001/orchestrator/health"

echo ""
echo "📝 Logs available at:"
echo "   /tmp/registry.log"
echo "   /tmp/orchestrator.log"
echo ""
echo "📍 Service PIDs saved to: $PIDS_FILE"
echo ""
echo "🎯 To stop all services:"
echo "   ./stop-core-services.sh"
echo ""
