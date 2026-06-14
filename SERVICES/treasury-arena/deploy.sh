#!/bin/bash
# Treasury Arena Deployment Script
# Ensures everything is running correctly with health checks

set -e

SERVER="root@198.54.123.234"
SERVICE_DIR="/opt/fpai/SERVICES/treasury-arena"
PORT=8021

echo "🚀 TREASURY ARENA DEPLOYMENT"
echo "=============================="
echo ""

# 1. Sync files
echo "📦 Syncing files to server..."
rsync -avz --exclude='*.pyc' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='*.db' \
  /Users/jamessunheart/Development/SERVICES/treasury-arena/ \
  $SERVER:$SERVICE_DIR/

echo "✅ Files synced"
echo ""

# 2. Update Nginx config (proper proxy without rewrite)
echo "🔧 Updating Nginx configuration..."
ssh $SERVER "cat > /etc/nginx/sites-available/treasury-arena <<'EOF'
location /treasury-arena/ {
    proxy_pass http://127.0.0.1:$PORT/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade \\\$http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host \\\$host;
    proxy_set_header X-Real-IP \\\$remote_addr;
    proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \\\$scheme;
    proxy_cache_bypass \\\$http_upgrade;

    # Disable caching
    add_header Cache-Control 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0';
    expires off;
}

location = /treasury-arena {
    return 301 /treasury-arena/;
}
EOF
"

echo "✅ Nginx config updated"
echo ""

# 3. Stop existing service
echo "🛑 Stopping existing service..."
ssh $SERVER "fuser -k $PORT/tcp 2>/dev/null || true"
sleep 2
echo "✅ Service stopped"
echo ""

# 4. Start service
echo "🚀 Starting Treasury Arena web server..."
ssh $SERVER "cd $SERVICE_DIR && nohup python3 -m uvicorn web.app:app --host 0.0.0.0 --port $PORT > /tmp/treasury_arena.log 2>&1 &"
sleep 4
echo "✅ Service started"
echo ""

# 5. Health check
echo "🏥 Running health check..."
HEALTH=$(ssh $SERVER "curl -s http://localhost:$PORT/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ Health check PASSED: $HEALTH"
else
    echo "❌ Health check FAILED"
    exit 1
fi
echo ""

# 6. Reload Nginx
echo "🔄 Reloading Nginx..."
ssh $SERVER "nginx -t && systemctl reload nginx"
echo "✅ Nginx reloaded"
echo ""

# 7. Final verification
echo "🎯 Final verification..."
sleep 2

STATUS=$(ssh $SERVER "curl -s http://localhost:$PORT/api/status")
echo "Local API Status: $STATUS"

echo ""
echo "🌐 Public URL verification..."
PUBLIC_HEALTH=$(curl -s https://fullpotential.com/treasury-arena/health || echo "FAILED")
if echo "$PUBLIC_HEALTH" | grep -q "healthy"; then
    echo "✅ PUBLIC URL WORKING: https://fullpotential.com/treasury-arena/"
else
    echo "⚠️  Public URL check: $PUBLIC_HEALTH"
fi

echo ""
echo "=============================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=============================="
echo ""
echo "🌐 Dashboard: https://fullpotential.com/treasury-arena/"
echo "🏥 Health:    https://fullpotential.com/treasury-arena/health"
echo "📊 API:       https://fullpotential.com/treasury-arena/api/status"
echo ""
echo "📝 Logs: ssh $SERVER 'tail -f /tmp/treasury_arena.log'"
echo ""
