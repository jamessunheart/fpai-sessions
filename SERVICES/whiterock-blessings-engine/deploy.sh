#!/bin/bash
# WhiteRock Blessings Engine - Deployment Script
# Deploy to Primary Server (198.54.123.234) on port 8020

set -e

# Configuration
SERVER="198.54.123.234"
SERVICE_NAME="whiterock-blessings"
SERVICE_PORT="8020"
DEPLOY_DIR="/opt/fpai/services/whiterock-blessings"

echo "🙏 WhiteRock Blessings Engine Deployment"
echo "=========================================="
echo "Target: $SERVER:$SERVICE_PORT"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check SSH connectivity
echo "📡 Checking SSH connectivity..."
if ! ssh -o ConnectTimeout=5 root@$SERVER "echo 'Connected'" 2>/dev/null; then
    echo "❌ Cannot connect to $SERVER. Try Tailscale VPN (ssh root@100.122.184.66)"
    exit 1
fi

# Create backup before deployment
echo "💾 Creating backup..."
ssh root@$SERVER "
    if [ -d $DEPLOY_DIR ]; then
        /opt/fpai/scripts/backup-service.sh whiterock-blessings pre-deploy service 2>/dev/null || true
    fi
"

# Create deployment directory
echo "📁 Creating deployment directory..."
ssh root@$SERVER "mkdir -p $DEPLOY_DIR"

# Copy files
echo "📦 Copying files..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'venv' \
    --exclude '.venv' \
    "$SCRIPT_DIR/" root@$SERVER:$DEPLOY_DIR/

# Create environment file
echo "🔧 Configuring environment..."
ssh root@$SERVER "
    cd $DEPLOY_DIR
    
    # Create .env if not exists
    if [ ! -f .env ]; then
        cp env.example .env
        
        # Generate secure JWT secret
        JWT_SECRET=\$(openssl rand -hex 32)
        sed -i \"s/your-secure-jwt-secret-change-this-in-production/\$JWT_SECRET/\" .env
        
        # Update database URL for local PostgreSQL
        sed -i 's|postgresql+asyncpg://postgres:postgres@db:5432/whiterock|postgresql+asyncpg://postgres:whiterock@localhost:5432/whiterock|' .env
        
        # Update Redis URL
        sed -i 's|redis://redis:6379/0|redis://localhost:6379/0|' .env
        
        echo '✅ Environment file created'
    fi
"

# Initialize PostgreSQL database
echo "🗄️ Setting up database..."
ssh root@$SERVER "
    # Create database if not exists
    sudo -u postgres psql -c \"SELECT 1 FROM pg_database WHERE datname = 'whiterock'\" | grep -q 1 || \
    sudo -u postgres psql -c \"CREATE DATABASE whiterock\"
    
    # Create user if not exists
    sudo -u postgres psql -c \"SELECT 1 FROM pg_roles WHERE rolname = 'postgres'\" | grep -q 1 || \
    sudo -u postgres psql -c \"CREATE USER postgres WITH PASSWORD 'whiterock'\"
    
    # Grant privileges
    sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE whiterock TO postgres\" 2>/dev/null || true
    
    # Run migrations
    cd $DEPLOY_DIR
    sudo -u postgres psql -d whiterock -f migrations/001_initial_schema.sql 2>/dev/null || true
"

# Create systemd service
echo "⚙️ Creating systemd service..."
ssh root@$SERVER "cat > /etc/systemd/system/fpai-whiterock-blessings.service << 'EOF'
[Unit]
Description=WhiteRock Blessings Engine
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_DIR
Environment=\"PATH=/usr/local/bin:/usr/bin:/bin\"
EnvironmentFile=$DEPLOY_DIR/.env
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port $SERVICE_PORT
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
"

# Install Python dependencies
echo "📚 Installing dependencies..."
ssh root@$SERVER "
    cd $DEPLOY_DIR
    pip3 install -r requirements.txt --quiet
"

# Start/restart service
echo "🚀 Starting service..."
ssh root@$SERVER "
    systemctl daemon-reload
    systemctl enable fpai-whiterock-blessings
    systemctl restart fpai-whiterock-blessings
    sleep 3
    systemctl status fpai-whiterock-blessings --no-pager || true
"

# Verify deployment
echo ""
echo "🔍 Verifying deployment..."
sleep 2

HEALTH=$(ssh root@$SERVER "curl -s http://localhost:$SERVICE_PORT/health" 2>/dev/null || echo "error")

if echo "$HEALTH" | grep -q "active"; then
    echo "✅ Health check passed!"
    echo ""
    echo "🎉 Deployment successful!"
    echo ""
    echo "📍 Service URL: http://$SERVER:$SERVICE_PORT"
    echo "📖 API Docs: http://$SERVER:$SERVICE_PORT/docs"
    echo "💓 Health: http://$SERVER:$SERVICE_PORT/health"
    echo ""
    echo "🌐 To expose via whiterock.us, ensure nginx config includes:"
    echo "   location / {"
    echo "       proxy_pass http://localhost:$SERVICE_PORT;"
    echo "   }"
else
    echo "⚠️ Service started but health check unclear"
    echo "Response: $HEALTH"
    echo ""
    echo "Check logs: ssh root@$SERVER journalctl -u fpai-whiterock-blessings -f"
fi

echo ""
echo "📋 Next steps:"
echo "   1. Configure Stripe API keys in .env"
echo "   2. Configure SendGrid API key for emails"
echo "   3. Update nginx for whiterock.us domain"
echo "   4. Create admin member account"



