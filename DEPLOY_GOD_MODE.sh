#!/bin/bash

echo "🚀 GOD MODE DEPLOYMENT SEQUENCE"
echo "---------------------------------"

# 1. Configuration
read -p "Server IP: " SERVER_IP
read -p "SSH User (Leave empty for 'root'): " SSH_USER
SSH_USER=${SSH_USER:-root}

echo "👉 Using SSH User: $SSH_USER"

echo ""
echo "🔐 SECURITY SETUP"
read -s -p "Set Dashboard Password: " DASH_PASS
echo ""
read -s -p "Confirm Password: " DASH_PASS_CONFIRM
echo ""

if [ "$DASH_PASS" != "$DASH_PASS_CONFIRM" ]; then
    echo "❌ Passwords do not match!"
    exit 1
fi

TARGET_DIR="/opt/fpai-god-mode"

echo ""
echo "📦 Packaging and Uploading to $SSH_USER@$SERVER_IP..."

# Ensure target dir exists first
ssh $SSH_USER@$SERVER_IP "mkdir -p $TARGET_DIR/god-mode"

# 2. Upload
rsync -avz --progress \
    --exclude 'node_modules' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '.git' \
    SERVICES/god-mode/ \
    $SSH_USER@$SERVER_IP:$TARGET_DIR/god-mode/

# Sync docs/core to parent
rsync -avz --progress \
    --exclude '.git' \
    docs core \
    $SSH_USER@$SERVER_IP:$TARGET_DIR/

# 3. Configure & Launch
echo ""
echo "🔥 Configuring Server..."

ssh $SSH_USER@$SERVER_IP "
    cd $TARGET_DIR/god-mode && \
    echo 'BASIC_AUTH_USER=architect' > .env && \
    echo 'BASIC_AUTH_PASS=$DASH_PASS' >> .env && \
    
    echo '⬇️  Stopping old containers...' && \
    docker-compose down --remove-orphans && \
    
    echo '🏗️  Building...' && \
    docker-compose build && \
    
    echo '🚀  Starting...' && \
    docker-compose up -d && \
    
    echo '⏳  Waiting for healthy status...' && \
    sleep 8 && \
    
    echo '🔍  Diagnostics:' && \
    docker-compose ps && \
    
    echo '📝 Backend Logs (Crash Debug):' && \
    docker-compose logs --tail=20 backend && \
    
    echo '🧪  Local Connectivity Check (Port 8080):' && \
    curl -I http://localhost:8080 || echo '❌ Local Curl Failed'
"

echo ""
echo "✅ DEPLOYMENT COMPLETE"
echo "🌍 Access God Mode at: http://$SERVER_IP:8080"
echo "   User: architect"
