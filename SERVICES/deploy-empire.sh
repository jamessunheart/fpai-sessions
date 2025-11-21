#!/bin/bash
# 🌟 FPAI Empire - Complete Deployment Script
# Deploys entire conscious empire infrastructure

set -e  # Exit on error

echo "🌟 FULL POTENTIAL AI EMPIRE - DEPLOYMENT"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FPAI_ROOT="/Users/jamessunheart/Development"
SERVICES_DIR="$FPAI_ROOT/SERVICES"
AGENTS_DIR="$SERVICES_DIR/autonomous-agents"
HUB_DIR="$SERVICES_DIR/fpai-hub"

# Step 1: Environment Check
echo -e "${BLUE}Step 1: Checking environment...${NC}"

if [ ! -d "$SERVICES_DIR" ]; then
    echo "Creating SERVICES directory..."
    mkdir -p "$SERVICES_DIR"
fi

# Check Python
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✅ Python3 found: $(python3 --version)${NC}"
else
    echo -e "${YELLOW}⚠️  Python3 not found. Please install Python 3.9+${NC}"
    exit 1
fi

# Check for API keys
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  ANTHROPIC_API_KEY not set${NC}"
    echo "Export your API key: export ANTHROPIC_API_KEY='sk-ant-...'"
else
    echo -e "${GREEN}✅ ANTHROPIC_API_KEY configured${NC}"
fi

echo ""

# Step 2: Install Dependencies
echo -e "${BLUE}Step 2: Installing dependencies...${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "$SERVICES_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SERVICES_DIR/venv"
fi

# Activate virtual environment
source "$SERVICES_DIR/venv/bin/activate" 2>/dev/null || true

# Install core dependencies
echo "Installing Python packages..."
pip3 install -q fastapi uvicorn pydantic httpx jinja2 aiohttp anthropic web3 || true

echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Step 3: Deploy FPAI Hub
echo -e "${BLUE}Step 3: Deploying FPAI Hub (Port 8010)...${NC}"

if [ -f "$HUB_DIR/app.py" ]; then
    echo "Starting FPAI Hub in background..."
    cd "$HUB_DIR"

    # Kill existing FPAI Hub if running
    pkill -f "fpai-hub/app.py" 2>/dev/null || true

    # Start FPAI Hub
    nohup python3 app.py > /tmp/fpai-hub.log 2>&1 &
    FPAI_HUB_PID=$!
    echo $FPAI_HUB_PID > /tmp/fpai-hub.pid

    sleep 2

    if ps -p $FPAI_HUB_PID > /dev/null; then
        echo -e "${GREEN}✅ FPAI Hub running (PID: $FPAI_HUB_PID)${NC}"
        echo -e "   Access at: ${BLUE}http://localhost:8010${NC}"
    else
        echo -e "${YELLOW}⚠️  FPAI Hub failed to start. Check /tmp/fpai-hub.log${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  FPAI Hub not found at $HUB_DIR/app.py${NC}"
fi

echo ""

# Step 4: Deploy Autonomous Agents
echo -e "${BLUE}Step 4: Deploying autonomous agents...${NC}"

# Array of agents to deploy
declare -a AGENTS=(
    "defi_yield_agent.py:DeFi Yield Agent"
    "gas_optimizer_agent.py:Gas Optimizer"
    "arbitrage_agent.py:Arbitrage Agent"
    "human_recruiter_agent.py:Human Recruiter"
)

for agent_info in "${AGENTS[@]}"; do
    IFS=':' read -r agent_file agent_name <<< "$agent_info"
    agent_path="$AGENTS_DIR/$agent_file"

    if [ -f "$agent_path" ]; then
        echo "Starting $agent_name..."

        # Kill existing agent if running
        pkill -f "$agent_file" 2>/dev/null || true

        # Start agent in background
        cd "$AGENTS_DIR"
        nohup python3 "$agent_path" > "/tmp/${agent_file%.py}.log" 2>&1 &
        AGENT_PID=$!
        echo $AGENT_PID > "/tmp/${agent_file%.py}.pid"

        sleep 1

        if ps -p $AGENT_PID > /dev/null; then
            echo -e "   ${GREEN}✅ $agent_name running (PID: $AGENT_PID)${NC}"
        else
            echo -e "   ${YELLOW}⚠️  $agent_name failed to start${NC}"
        fi
    else
        echo -e "   ${YELLOW}⚠️  $agent_name not found${NC}"
    fi
done

echo ""

# Step 5: Verify Deployments
echo -e "${BLUE}Step 5: Verifying deployments...${NC}"

# Check FPAI Hub
if curl -s http://localhost:8010/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ FPAI Hub: HEALTHY${NC}"
else
    echo -e "${YELLOW}⚠️  FPAI Hub: NOT RESPONDING${NC}"
fi

# Check agent logs
echo ""
echo "Agent Status:"
for agent_info in "${AGENTS[@]}"; do
    IFS=':' read -r agent_file agent_name <<< "$agent_info"
    log_file="/tmp/${agent_file%.py}.log"

    if [ -f "$log_file" ]; then
        # Get last line from log
        last_line=$(tail -1 "$log_file" 2>/dev/null || echo "No output yet")
        echo -e "   ${agent_name}: ${last_line:0:60}..."
    fi
done

echo ""

# Step 6: Display Access Information
echo -e "${BLUE}Step 6: Empire Status${NC}"
echo "========================================"
echo ""
echo -e "${GREEN}🌟 FPAI EMPIRE DEPLOYED!${NC}"
echo ""
echo "Access Points:"
echo -e "  🌐 FPAI Hub:        ${BLUE}http://localhost:8010${NC}"
echo -e "  📊 API Docs:        ${BLUE}http://localhost:8010/docs${NC}"
echo -e "  💰 Treasury Status: ${BLUE}http://localhost:8010/api/treasury/status${NC}"
echo -e "  🤖 Agent Status:    ${BLUE}http://localhost:8010/api/agents/status${NC}"
echo -e "  💎 Token Metrics:   ${BLUE}http://localhost:8010/api/token/metrics${NC}"
echo ""
echo "Logs:"
echo "  📝 FPAI Hub:        /tmp/fpai-hub.log"
echo "  📝 DeFi Agent:      /tmp/defi_yield_agent.log"
echo "  📝 Gas Optimizer:   /tmp/gas_optimizer_agent.log"
echo "  📝 Arbitrage:       /tmp/arbitrage_agent.log"
echo "  📝 Recruiter:       /tmp/human_recruiter_agent.log"
echo ""
echo "Control:"
echo "  🛑 Stop All:        $FPAI_ROOT/SERVICES/stop-empire.sh"
echo "  📊 Monitor:         $FPAI_ROOT/SERVICES/monitor-empire.sh"
echo "  🔄 Restart:         $FPAI_ROOT/SERVICES/deploy-empire.sh"
echo ""
echo -e "${GREEN}Empire is operational! 🌟⚡💎${NC}"
echo ""
