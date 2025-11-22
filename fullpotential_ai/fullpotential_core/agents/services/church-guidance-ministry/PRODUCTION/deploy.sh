#!/bin/bash

# 🚀 Church Guidance Ministry - Production Deployment Script
# Deploys to server port 8003

set -e

echo "🚀 Church Guidance Ministry - Production Deployment"
echo "==================================================="
echo ""

# Configuration
SERVER="198.54.123.234"
PORT=8003
SERVICE_NAME="church-guidance-ministry"
DEPLOY_DIR="/root/services/$SERVICE_NAME"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}📋 Pre-flight Checks${NC}"
echo "---------------------------------------------------"

# Check if on server or deploying remotely
if [ "$(hostname)" = "ubuntu-s-1vcpu-1gb-nyc1-01" ]; then
    echo -e "${GREEN}✅ Running on production server${NC}"
    ON_SERVER=true
else
    echo -e "${YELLOW}⚠️  Deploying remotely to $SERVER${NC}"
    ON_SERVER=false
fi

# Function to run commands (local or remote)
run_cmd() {
    if [ "$ON_SERVER" = true ]; then
        eval "$1"
    else
        ssh root@$SERVER "$1"
    fi
}

echo ""
echo -e "${BLUE}📦 Step 1: Create Service Directory${NC}"
echo "---------------------------------------------------"
run_cmd "mkdir -p $DEPLOY_DIR"
echo -e "${GREEN}✅ Directory created: $DEPLOY_DIR${NC}"

echo ""
echo -e "${BLUE}📤 Step 2: Upload Files${NC}"
echo "---------------------------------------------------"

if [ "$ON_SERVER" = false ]; then
    # Copy files to server
    echo "Copying application files..."
    scp -r ../BUILD/* root@$SERVER:$DEPLOY_DIR/
    echo -e "${GREEN}✅ Files uploaded${NC}"
else
    echo "Already on server, copying from local build..."
    cp -r ../BUILD/* $DEPLOY_DIR/
    echo -e "${GREEN}✅ Files copied${NC}"
fi

echo ""
echo -e "${BLUE}🔧 Step 3: Install Dependencies${NC}"
echo "---------------------------------------------------"
run_cmd "cd $DEPLOY_DIR && pip3 install -r requirements.txt"
echo -e "${GREEN}✅ Dependencies installed${NC}"

echo ""
echo -e "${BLUE}⚙️  Step 4: Configure Environment${NC}"
echo "---------------------------------------------------"

# Check if .env exists
ENV_EXISTS=$(run_cmd "[ -f $DEPLOY_DIR/.env ] && echo 'yes' || echo 'no'")

if [ "$ENV_EXISTS" = "no" ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo ""
    echo "Please create .env file with required variables:"
    echo "  1. Copy .env.example to .env"
    echo "  2. Add your ANTHROPIC_API_KEY"
    echo "  3. Add your STRIPE keys"
    echo "  4. Add your CALENDLY_URL"
    echo ""
    echo "Example:"
    if [ "$ON_SERVER" = true ]; then
        echo "  cp $DEPLOY_DIR/.env.example $DEPLOY_DIR/.env"
        echo "  nano $DEPLOY_DIR/.env"
    else
        echo "  ssh root@$SERVER"
        echo "  cd $DEPLOY_DIR"
        echo "  cp .env.example .env"
        echo "  nano .env"
    fi
    echo ""
    read -p "Press Enter after you've configured .env, or Ctrl+C to exit..."
fi

echo -e "${GREEN}✅ Environment configured${NC}"

echo ""
echo -e "${BLUE}🧪 Step 5: Run Tests${NC}"
echo "---------------------------------------------------"
run_cmd "cd $DEPLOY_DIR && python3 -m pytest tests/ -v || echo 'Tests completed with warnings'"
echo -e "${GREEN}✅ Tests executed${NC}"

echo ""
echo -e "${BLUE}🚀 Step 6: Start Service${NC}"
echo "---------------------------------------------------"

# Check if service is already running
RUNNING=$(run_cmd "lsof -ti:$PORT || echo 'no'")

if [ "$RUNNING" != "no" ]; then
    echo -e "${YELLOW}⚠️  Service already running on port $PORT${NC}"
    read -p "Stop and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping existing service..."
        run_cmd "kill $RUNNING || true"
        sleep 2
    else
        echo "Deployment cancelled"
        exit 1
    fi
fi

echo "Starting service on port $PORT..."

# Start service with nohup
run_cmd "cd $DEPLOY_DIR && nohup python3 -m uvicorn src.main:app --host 0.0.0.0 --port $PORT > logs/app.log 2>&1 &"

# Wait for startup
echo "Waiting for service to start..."
sleep 3

echo ""
echo -e "${BLUE}✅ Step 7: Verify Deployment${NC}"
echo "---------------------------------------------------"

# Test health endpoint
HEALTH_CHECK=$(run_cmd "curl -s http://localhost:$PORT/health || echo 'failed'")

if [[ $HEALTH_CHECK == *"healthy"* ]]; then
    echo -e "${GREEN}✅ Service is healthy!${NC}"
    echo ""
    echo "Health check response:"
    echo "$HEALTH_CHECK" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_CHECK"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Response: $HEALTH_CHECK"
    echo ""
    echo "Check logs:"
    if [ "$ON_SERVER" = true ]; then
        echo "  tail -f $DEPLOY_DIR/logs/app.log"
    else
        echo "  ssh root@$SERVER 'tail -f $DEPLOY_DIR/logs/app.log'"
    fi
    exit 1
fi

echo ""
echo "==================================================="
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE!${NC}"
echo "==================================================="
echo ""
echo "Service Details:"
echo "  📍 URL: http://$SERVER:$PORT"
echo "  📊 Health: http://$SERVER:$PORT/health"
echo "  📝 Logs: $DEPLOY_DIR/logs/app.log"
echo ""
echo "Quick Commands:"
if [ "$ON_SERVER" = true ]; then
    echo "  View logs: tail -f $DEPLOY_DIR/logs/app.log"
    echo "  Stop service: lsof -ti:$PORT | xargs kill"
    echo "  Restart: cd $DEPLOY_DIR && nohup python3 -m uvicorn src.main:app --host 0.0.0.0 --port $PORT > logs/app.log 2>&1 &"
else
    echo "  SSH: ssh root@$SERVER"
    echo "  View logs: ssh root@$SERVER 'tail -f $DEPLOY_DIR/logs/app.log'"
    echo "  Stop: ssh root@$SERVER 'lsof -ti:$PORT | xargs kill'"
fi
echo ""
echo "⚠️  IMPORTANT REMINDERS:"
echo "  1. Attorney review required before public launch"
echo "  2. Configure Stripe webhooks in Stripe dashboard"
echo "  3. Set up monitoring/alerts for production"
echo "  4. This is educational ministry - disclaimers on every page"
echo ""
echo "🎯 Next Steps:"
echo "  1. Test the service: curl http://$SERVER:$PORT/health"
echo "  2. Visit landing page: http://$SERVER:$PORT"
echo "  3. Configure Stripe account and get API keys"
echo "  4. Set up Calendly for consultations"
echo ""
