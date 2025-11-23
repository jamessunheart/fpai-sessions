#!/bin/bash

echo "🚀 GOD MODE DEPLOYMENT SEQUENCE"
echo "---------------------------------"

# 1. Configuration
read -p "Server IP: " SERVER_IP
read -p "SSH User (default: root): " SSH_USER
SSH_USER=${SSH_USER:-root}
TARGET_DIR="/opt/fpai-god-mode"

echo ""
echo "📦 Packaging and Uploading to $SSH_USER@$SERVER_IP..."

# 2. Upload (Using rsync to exclude junk)
# We need: SERVICES/god-mode, docs/, core/
rsync -avz --progress \
    --exclude 'node_modules' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '.git' \
    SERVICES/god-mode \
    docs \
    core \
    $SSH_USER@$SERVER_IP:$TARGET_DIR

# 3. Launch
echo ""
echo "🔥 Launching Containers..."
ssh $SSH_USER@$SERVER_IP "cd $TARGET_DIR/SERVICES/god-mode && docker-compose up -d --build"

echo ""
echo "✅ DEPLOYMENT COMPLETE"
echo "🌍 Access God Mode at: http://$SERVER_IP"

