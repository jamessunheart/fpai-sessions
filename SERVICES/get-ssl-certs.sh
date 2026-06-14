#!/bin/bash

# Get SSL Certificates for Full Potential .com Subdomains
# Run this once DNS has propagated

set -e

SERVER="198.54.123.234"
SERVER_USER="root"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 OBTAINING SSL CERTIFICATES FOR SUBDOMAINS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh ${SERVER_USER}@${SERVER} << 'ENDSSH'

# Define subdomains to certify
SUBDOMAINS=(
    "api.fullpotential.com"
    "match.fullpotential.com"
    "membership.fullpotential.com"
    "jobs.fullpotential.com"
    "registry.fullpotential.com"
)

# Obtain certificate for each subdomain
for domain in "${SUBDOMAINS[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📜 Processing: $domain"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Try to obtain certificate
    certbot --nginx -d "$domain" --non-interactive --agree-tos --email admin@fullpotential.com --redirect

    if [ $? -eq 0 ]; then
        echo "✅ Certificate obtained for $domain"
    else
        echo "⚠️  Failed to obtain certificate for $domain (may need more time for DNS propagation)"
    fi

    echo ""
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 Reloading nginx..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
nginx -t && systemctl reload nginx

echo ""
echo "✅ SSL certificate setup complete!"
echo ""

ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TESTING HTTPS ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test each subdomain
SUBDOMAINS=(
    "https://api.fullpotential.com/health"
    "https://match.fullpotential.com/health"
    "https://membership.fullpotential.com"
    "https://jobs.fullpotential.com"
    "https://registry.fullpotential.com/health"
)

for url in "${SUBDOMAINS[@]}"; do
    echo -n "Testing $url ... "
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")

    if [[ "$response" == "200" ]]; then
        echo "✅ OK"
    elif [[ "$response" == "301" || "$response" == "302" ]]; then
        echo "✅ OK (redirect)"
    else
        echo "❌ FAILED (HTTP $response)"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DOMAIN SETUP COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Your services are now available at:"
echo ""
echo "  Main Site:       https://fullpotential.com"
echo "  Dashboard:       https://dashboard.fullpotential.com"
echo "  AI API:          https://api.fullpotential.com"
echo "  Match API:       https://match.fullpotential.com"
echo "  Membership:      https://membership.fullpotential.com"
echo "  Jobs:            https://jobs.fullpotential.com"
echo "  Registry:        https://registry.fullpotential.com"
echo "  White Rock:      https://whiterock.us"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
