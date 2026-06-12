#!/bin/bash
# FPAI Infrastructure Startup Script
# Starts all TIER 0 foundational services in correct order
# Built by: Forge (Session #1)
# Purpose: One-command infrastructure deployment

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   FPAI INFRASTRUCTURE STARTUP${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

BASE_DIR="/Users/jamessunheart/Development"
cd "$BASE_DIR"

# Function to check if service is running on a port
check_port() {
    local port=$1
    lsof -i :$port >/dev/null 2>&1
    return $?
}

# Function to wait for service health
wait_for_health() {
    local port=$1
    local endpoint=${2:-/health}
    local max_attempts=30
    local attempt=0

    echo -n "   Waiting for port $port$endpoint..."

    while [ $attempt -lt $max_attempts ]; do
        if curl -s --max-time 1 "http://localhost:$port$endpoint" >/dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        sleep 1
        ((attempt++))
        echo -n "."
    done

    echo -e " ${RED}✗${NC}"
    return 1
}

# Function to start a service
start_service() {
    local name=$1
    local port=$2
    local dir=$3
    local start_cmd=$4
    local health_endpoint=${5:-/health}

    echo -e "${CYAN}→ Starting $name (port $port)${NC}"

    # Check if already running
    if check_port $port; then
        echo -e "   ${YELLOW}Already running${NC}"
        # Verify health
        if curl -s --max-time 2 "http://localhost:$port$health_endpoint" >/dev/null 2>&1; then
            echo -e "   ${GREEN}✓ Healthy${NC}"
            return 0
        else
            echo -e "   ${YELLOW}⚠ Running but unhealthy, restarting...${NC}"
            # Kill the process
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
            sleep 2
        fi
    fi

    # Start the service
    cd "$BASE_DIR/$dir"

    # Check if venv exists
    if [ ! -d "venv" ]; then
        echo -e "   ${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi

    # Activate venv and install requirements if needed
    source venv/bin/activate

    if [ -f "requirements.txt" ] && [ ! -f "venv/.requirements_installed" ]; then
        echo -e "   ${YELLOW}Installing requirements...${NC}"
        pip install -q -r requirements.txt
        touch venv/.requirements_installed
    fi

    # Start service in background
    nohup $start_cmd > "/tmp/${name}.log" 2>&1 &
    local pid=$!

    echo -e "   ${GREEN}Started (PID: $pid)${NC}"

    # Wait for health check
    if wait_for_health $port "$health_endpoint"; then
        echo -e "   ${GREEN}✓ $name ready${NC}"
        echo ""
        return 0
    else
        echo -e "   ${RED}✗ $name failed to start${NC}"
        echo -e "   ${YELLOW}Check logs: /tmp/${name}.log${NC}"
        echo ""
        return 1
    fi
}

# TIER 0: Core Infrastructure Services
echo -e "${BLUE}━━━ TIER 0: Core Infrastructure ━━━${NC}"
echo ""

# 1. Registry (Port 8000) - Service Discovery
start_service "Registry" 8000 "agents/services/registry" \
    "uvicorn app.main:app --host 0.0.0.0 --port 8000" \
    "/health"

# 2. Orchestrator (Port 8001) - Task Routing
start_service "Orchestrator" 8001 "agents/services/orchestrator" \
    "uvicorn app.main:app --host 0.0.0.0 --port 8001" \
    "/orchestrator/health"

# 3. SPEC Verifier (Port 8002) - Service Validation
if [ -d "agents/services/spec-verifier" ]; then
    start_service "SPEC-Verifier" 8002 "agents/services/spec-verifier" \
        "uvicorn app.main:app --host 0.0.0.0 --port 8002" \
        "/health"
fi

echo -e "${BLUE}━━━ TIER 0.5: Coordination & Communication ━━━${NC}"
echo ""

# 4. Unified Chat (Port 8100) - Session Coordination
if [ -d "agents/services/unified-chat" ]; then
    start_service "Unified-Chat" 8100 "agents/services/unified-chat" \
        "python3 main_secure.py" \
        "/api/health"
fi

# 5. FPAI Hub (Port 8010) - Service Hub
if [ -d "agents/services/fpai-hub" ]; then
    start_service "FPAI-Hub" 8010 "agents/services/fpai-hub" \
        "uvicorn main:app --host 0.0.0.0 --port 8010" \
        "/health"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ INFRASTRUCTURE STARTUP COMPLETE${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Summary
echo -e "${CYAN}Service Status:${NC}"
echo ""

for port in 8000 8001 8002 8010 8100; do
    service_name=$(case $port in
        8000) echo "Registry" ;;
        8001) echo "Orchestrator" ;;
        8002) echo "SPEC Verifier" ;;
        8010) echo "FPAI Hub" ;;
        8100) echo "Unified Chat" ;;
    esac)

    if check_port $port; then
        echo -e "  ${GREEN}✓${NC} $service_name (port $port)"
    else
        echo -e "  ${RED}✗${NC} $service_name (port $port) ${YELLOW}[OFFLINE]${NC}"
    fi
done

echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo "  - View service health: curl http://localhost:8000/health"
echo "  - Access Unified Chat: http://localhost:8100"
echo "  - Connect sessions: cd agents/services/unified-chat && python3 connect_session.py"
echo "  - View SSOT: cat docs/coordination/SSOT.json"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
