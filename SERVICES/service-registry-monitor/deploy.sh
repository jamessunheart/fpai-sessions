#!/bin/bash

# Deploy Service Registry Monitor to server

SERVER="root@198.54.123.234"
SERVICE_DIR="/root/SERVICES/service-registry-monitor"

echo "🚀 Deploying Service Registry Monitor..."

# Create directory on server
ssh $SERVER "mkdir -p $SERVICE_DIR"

# Copy files
echo "📦 Copying files..."
scp monitor.py $SERVER:$SERVICE_DIR/
scp requirements.txt $SERVER:$SERVICE_DIR/

# Install dependencies
echo "📦 Installing dependencies..."
ssh $SERVER "cd $SERVICE_DIR && pip3 install -r requirements.txt --quiet"

# Make executable
ssh $SERVER "chmod +x $SERVICE_DIR/monitor.py"

# Test run once
echo "🧪 Test run..."
ssh $SERVER "cd $SERVICE_DIR && python3 monitor.py --once"

echo "✅ Deployment complete!"
echo ""
echo "To run continuously:"
echo "  ssh $SERVER 'cd $SERVICE_DIR && python3 monitor.py > /tmp/service-monitor.log 2>&1 &'"
