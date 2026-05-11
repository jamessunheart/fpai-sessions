#!/bin/bash
# Setup chat.fullpotential.com with SSL

set -e

echo "🌐 Setting up chat.fullpotential.com"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check DNS first
echo "📍 Checking DNS propagation..."
if nslookup chat.fullpotential.com | grep -q "198.54.123.234"; then
    echo "✅ DNS is propagated!"
    DNS_READY=true
else
    echo "⏳ DNS not yet propagated"
    echo ""
    echo "Please add this DNS record in Namecheap:"
    echo ""
    echo "  Domain: fullpotential.com"
    echo "  Type:   A Record"
    echo "  Host:   chat"
    echo "  Value:  198.54.123.234"
    echo "  TTL:    Automatic"
    echo ""
    echo "Go to: https://ap.www.namecheap.com/"
    echo "Then run this script again in 5-10 minutes"
    echo ""
    DNS_READY=false
fi

if [ "$DNS_READY" = false ]; then
    exit 1
fi

echo ""
echo "🔒 Getting SSL certificate..."
echo ""

# Get SSL certificate on production server
ssh root@198.54.123.234 << 'ENDSSH'
# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Get certificate for both .com and .ai
certbot --nginx \
    -d chat.fullpotential.com \
    -d chat.fullpotential.ai \
    --non-interactive \
    --agree-tos \
    --redirect \
    --email james@fullpotential.com

echo ""
echo "✅ SSL certificate installed!"
echo "✅ HTTPS redirect enabled!"

# Restart nginx to be sure
systemctl reload nginx

ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 COMPLETE!"
echo ""
echo "Your unified chat is now live at:"
echo ""
echo "  🌐 https://chat.fullpotential.com"
echo "  🌐 https://chat.fullpotential.ai"
echo ""
echo "Password: 9MzqXYQwKHTmONFVY2aEZ9slJhNU5I4F"
echo ""
echo "Share this URL with anyone you want to give access!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
