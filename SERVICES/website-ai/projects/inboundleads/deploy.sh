#!/bin/bash
# =============================================================================
# DEPLOY INBOUND LEADS PROJECT PAGE
# =============================================================================
# Deploys the project page to fullpotential.ai/projects/inboundleads/
#
# Usage: ./deploy.sh
# Requires: SSH access to 198.54.123.234

set -e

# Use Tailscale VPN IP when external SSH is down
# External: 198.54.123.234 | Tailscale: 100.122.184.66
SERVER="100.122.184.66"
LOCAL_DIR="$(dirname "$0")"
REMOTE_DIR="/var/www/fullpotential.ai/projects/inboundleads"

echo "🚀 Deploying Inbound Leads Project Page..."
echo ""

# Create remote directory
echo "📁 Creating directory on server..."
ssh "root@$SERVER" "mkdir -p $REMOTE_DIR"

# Copy files
echo "📤 Copying files..."
scp "$LOCAL_DIR/index.html" "root@$SERVER:$REMOTE_DIR/"
scp "$LOCAL_DIR/project.json" "root@$SERVER:$REMOTE_DIR/"

# Set permissions
echo "🔒 Setting permissions..."
ssh "root@$SERVER" "chmod 644 $REMOTE_DIR/*"

# Test deployment
echo "🧪 Testing deployment..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://fullpotential.ai/projects/inboundleads/" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Deployment successful!"
    echo ""
    echo "🌐 Live URL: https://fullpotential.ai/projects/inboundleads/"
else
    echo "⚠️ HTTP $HTTP_CODE - May need nginx configuration"
    echo ""
    echo "📝 If nginx needs updating, run this on the server:"
    echo ""
    echo 'cat >> /etc/nginx/sites-available/fullpotential.ai << EOF

location /projects/ {
    alias /var/www/fullpotential.ai/projects/;
    index index.html;
    try_files $uri $uri/ =404;
}
EOF'
    echo ""
    echo "Then: systemctl reload nginx"
fi

echo ""
echo "Done!"

