#!/bin/bash
# =============================================================================
# COCOON Command Center - Deployment Script
# Deploys to primary server: 198.54.123.234
# =============================================================================

set -e

# Configuration
SERVER="198.54.123.234"
SERVER_USER="root"
DEPLOY_PATH="/opt/fpai/cocoon"
SERVICE_NAME="fpai-cocoon"
PORT=8650

echo "🥚 COCOON Command Center - Deployment"
echo "======================================="

# Check if running locally or already on server
if [[ $(hostname -I 2>/dev/null | grep -c "$SERVER") -gt 0 ]] || [[ "$1" == "--local" ]]; then
    echo "Running on server..."
    
    # Create directory
    mkdir -p $DEPLOY_PATH/static
    
    # Copy files
    cp server.py $DEPLOY_PATH/
    cp requirements.txt $DEPLOY_PATH/
    cp -r static/* $DEPLOY_PATH/static/
    
    # Create virtual environment if needed
    if [ ! -d "$DEPLOY_PATH/venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv $DEPLOY_PATH/venv
    fi
    
    # Install dependencies
    echo "Installing dependencies..."
    $DEPLOY_PATH/venv/bin/pip install -r $DEPLOY_PATH/requirements.txt
    
    # Create systemd service
    echo "Creating systemd service..."
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=COCOON Command Center
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_PATH
ExecStart=$DEPLOY_PATH/venv/bin/python server.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and start service
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    systemctl restart $SERVICE_NAME
    
    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "Service status:"
    systemctl status $SERVICE_NAME --no-pager
    echo ""
    echo "🌐 COCOON Command Center running at:"
    echo "   http://$SERVER:$PORT"
    echo ""
    
else
    echo "Deploying to server $SERVER..."
    
    # Create temp directory for upload
    TEMP_DIR=$(mktemp -d)
    cp server.py requirements.txt $TEMP_DIR/
    cp -r static $TEMP_DIR/
    cp deploy.sh $TEMP_DIR/
    
    # Upload to server
    echo "Uploading files..."
    scp -r $TEMP_DIR/* $SERVER_USER@$SERVER:/tmp/cocoon-deploy/
    
    # Run deployment on server
    echo "Running deployment on server..."
    ssh $SERVER_USER@$SERVER "cd /tmp/cocoon-deploy && bash deploy.sh --local"
    
    # Cleanup
    rm -rf $TEMP_DIR
    ssh $SERVER_USER@$SERVER "rm -rf /tmp/cocoon-deploy"
    
    echo ""
    echo "✅ Remote deployment complete!"
    echo ""
    echo "🌐 COCOON Command Center available at:"
    echo "   http://$SERVER:$PORT"
    echo ""
fi


