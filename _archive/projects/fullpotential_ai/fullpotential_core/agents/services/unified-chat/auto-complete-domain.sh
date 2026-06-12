#!/bin/bash
# Auto-monitor DNS and complete domain setup when ready

set -e

DOMAIN="chat.fullpotential.com"
SERVER_IP="198.54.123.234"

echo "🔄 Monitoring DNS propagation for $DOMAIN..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "I'll check every 30 seconds and auto-complete setup when DNS is ready."
echo ""
echo "⏳ Waiting for you to add this DNS record in Namecheap:"
echo ""
echo "   Domain:  fullpotential.com"
echo "   Type:    A Record"
echo "   Host:    chat"
echo "   Value:   198.54.123.234"
echo "   TTL:     1 min"
echo ""
echo "Add it here: https://ap.www.namecheap.com/"
echo "  → Domain List → fullpotential.com → Manage → Advanced DNS"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Counter for attempts
ATTEMPTS=0
MAX_ATTEMPTS=120  # 1 hour max wait

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    ATTEMPTS=$((ATTEMPTS + 1))

    # Check DNS
    if nslookup $DOMAIN 2>&1 | grep -q "$SERVER_IP"; then
        echo ""
        echo "✅ DNS PROPAGATED!"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🔒 Getting SSL Certificate..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""

        # Get SSL certificate on server
        ssh root@198.54.123.234 << 'ENDSSH'
set -e

# Install certbot if needed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt-get update -qq
    apt-get install -y certbot python3-certbot-nginx
fi

# Get certificate
echo "Requesting SSL certificate..."
certbot --nginx \
    -d chat.fullpotential.com \
    -d chat.fullpotential.ai \
    --non-interactive \
    --agree-tos \
    --redirect \
    --email james@fullpotential.com || {
        echo "Note: .ai domain might not be configured yet, trying .com only..."
        certbot --nginx \
            -d chat.fullpotential.com \
            --non-interactive \
            --agree-tos \
            --redirect \
            --email james@fullpotential.com
    }

echo ""
echo "✅ SSL certificate installed!"

# Reload nginx
systemctl reload nginx

echo "✅ Nginx reloaded with HTTPS enabled!"

ENDSSH

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🎉 COMPLETE!"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Your unified chat is now live at:"
        echo ""
        echo "  🌐 https://chat.fullpotential.com"
        echo ""
        echo "Password: 9MzqXYQwKHTmONFVY2aEZ9slJhNU5I4F"
        echo ""
        echo "Share this URL with anyone you want to give access!"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        exit 0
    else
        # Show progress
        MINUTES=$((ATTEMPTS / 2))
        echo -ne "\r[Attempt $ATTEMPTS/$MAX_ATTEMPTS - ${MINUTES}min] Still waiting for DNS..."
        sleep 30
    fi
done

echo ""
echo ""
echo "⏱️  Timeout after 1 hour. DNS may take longer to propagate."
echo "   Run this script again later, or check manually:"
echo "   nslookup chat.fullpotential.com"
echo ""
