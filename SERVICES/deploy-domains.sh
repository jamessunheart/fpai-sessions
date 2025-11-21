#!/bin/bash

# Deploy Domain Configuration for Full Potential AI
# Sets up nginx reverse proxy with SSL for all services

set -e

SERVER="198.54.123.234"
SERVER_USER="root"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 DEPLOYING DOMAIN CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Upload nginx configuration
echo "📤 Uploading nginx configuration..."
scp nginx-domain-config.conf ${SERVER_USER}@${SERVER}:/etc/nginx/sites-available/fpai-domains.conf

# Configure on server
echo "⚙️  Configuring nginx..."
ssh ${SERVER_USER}@${SERVER} << 'ENDSSH'

# Remove default site if it exists
rm -f /etc/nginx/sites-enabled/default

# Enable our configuration
ln -sf /etc/nginx/sites-available/fpai-domains.conf /etc/nginx/sites-enabled/fpai-domains.conf

# Test nginx configuration
echo ""
echo "🧪 Testing nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration valid"

    # Reload nginx
    echo ""
    echo "🔄 Reloading nginx..."
    systemctl reload nginx
    systemctl status nginx --no-pager | head -10

    echo ""
    echo "✅ Nginx reloaded successfully"
else
    echo "❌ Nginx configuration test failed"
    exit 1
fi

ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 SETTING UP SSL CERTIFICATES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Install certbot if needed
ssh ${SERVER_USER}@${SERVER} << 'ENDSSH'

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
else
    echo "✅ Certbot already installed"
fi

echo ""
echo "🔐 Obtaining SSL certificates..."
echo ""

# Define all domains
DOMAINS=(
    "fullpotential.com,www.fullpotential.com"
    "fullpotential.ai,www.fullpotential.ai"
    "dashboard.fullpotential.com,dashboard.fullpotential.ai"
    "api.fullpotential.com,api.fullpotential.ai"
    "match.fullpotential.com,match.fullpotential.ai"
    "membership.fullpotential.com,membership.fullpotential.ai"
    "jobs.fullpotential.com,jobs.fullpotential.ai"
    "registry.fullpotential.com,registry.fullpotential.ai"
    "whiterock.us,www.whiterock.us"
)

# Obtain certificates for each domain group
for domain_group in "${DOMAINS[@]}"; do
    echo "📜 Processing: $domain_group"

    # Convert comma-separated list to -d flags
    domain_flags=""
    IFS=',' read -ra ADDR <<< "$domain_group"
    for domain in "${ADDR[@]}"; do
        domain_flags="$domain_flags -d $domain"
    done

    # Try to obtain certificate
    certbot --nginx $domain_flags --non-interactive --agree-tos --email admin@fullpotential.com --redirect || echo "⚠️  Certificate for $domain_group may already exist or failed"

    echo ""
done

echo ""
echo "✅ SSL certificate setup complete"

# Set up auto-renewal
echo ""
echo "🔄 Setting up auto-renewal..."
systemctl enable certbot.timer
systemctl start certbot.timer
echo "✅ Auto-renewal enabled"

ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TESTING DOMAIN ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test each domain
DOMAINS=(
    "http://fullpotential.com"
    "http://fullpotential.ai"
    "http://dashboard.fullpotential.com"
    "http://api.fullpotential.com/health"
    "http://match.fullpotential.com/health"
    "http://membership.fullpotential.com"
    "http://jobs.fullpotential.com"
    "http://whiterock.us"
)

for url in "${DOMAINS[@]}"; do
    echo -n "Testing $url ... "
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" | grep -q "200\|301\|302"; then
        echo "✅ OK"
    else
        echo "❌ FAILED"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DOMAIN DEPLOYMENT COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Your services are now available at:"
echo ""
echo "FULL POTENTIAL AI:"
echo "  Main Site:       https://fullpotential.com"
echo "  Dashboard:       https://dashboard.fullpotential.com"
echo "  AI API:          https://api.fullpotential.com"
echo "  Match API:       https://match.fullpotential.com"
echo "  Membership:      https://membership.fullpotential.com"
echo "  Jobs:            https://jobs.fullpotential.com"
echo ""
echo "WHITE ROCK MINISTRY:"
echo "  Main Site:       https://whiterock.us"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
