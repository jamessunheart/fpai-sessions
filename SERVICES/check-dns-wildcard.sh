#!/bin/bash

# DNS Wildcard Diagnostic Tool
# Checks if wildcard DNS is working for fullpotential.com

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 DNS WILDCARD DIAGNOSTIC"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

DOMAIN="fullpotential.com"
SERVER_IP="198.54.123.234"

# Test main domain
echo "1️⃣  Testing main domain: $DOMAIN"
MAIN_IP=$(dig +short $DOMAIN @8.8.8.8 | tail -1)
if [ "$MAIN_IP" == "$SERVER_IP" ]; then
    echo "   ✅ $DOMAIN → $MAIN_IP (correct)"
else
    echo "   ⚠️  $DOMAIN → $MAIN_IP (expected $SERVER_IP)"
fi
echo ""

# Test known working subdomain
echo "2️⃣  Testing known subdomain: dashboard.$DOMAIN"
DASH_IP=$(dig +short dashboard.$DOMAIN @8.8.8.8 | tail -1)
if [ "$DASH_IP" == "$SERVER_IP" ]; then
    echo "   ✅ dashboard.$DOMAIN → $DASH_IP (working)"
else
    echo "   ❌ dashboard.$DOMAIN → $DASH_IP (not working)"
fi
echo ""

# Test wildcard with random subdomain
echo "3️⃣  Testing wildcard with random subdomain"
RANDOM_SUB="test$(date +%s)"
RANDOM_IP=$(dig +short ${RANDOM_SUB}.$DOMAIN @8.8.8.8 | tail -1)
if [ "$RANDOM_IP" == "$SERVER_IP" ]; then
    echo "   ✅ ${RANDOM_SUB}.$DOMAIN → $RANDOM_IP"
    echo "   ✅ WILDCARD IS WORKING! 🎉"
    WILDCARD_WORKS=true
else
    echo "   ❌ ${RANDOM_SUB}.$DOMAIN → No response"
    echo "   ❌ WILDCARD NOT WORKING"
    WILDCARD_WORKS=false
fi
echo ""

# Test specific subdomains we need
echo "4️⃣  Testing required subdomains:"
SUBDOMAINS=("api" "match" "membership" "jobs" "registry")

for sub in "${SUBDOMAINS[@]}"; do
    IP=$(dig +short ${sub}.$DOMAIN @8.8.8.8 | tail -1)
    if [ "$IP" == "$SERVER_IP" ]; then
        echo "   ✅ ${sub}.$DOMAIN → $IP"
    else
        echo "   ❌ ${sub}.$DOMAIN → No response (NXDOMAIN)"
    fi
done
echo ""

# Check with different DNS servers
echo "5️⃣  Checking across multiple DNS servers:"
DNS_SERVERS=("8.8.8.8:Google" "1.1.1.1:Cloudflare" "208.67.222.222:OpenDNS")

for server in "${DNS_SERVERS[@]}"; do
    IP="${server%%:*}"
    NAME="${server##*:}"
    RESULT=$(dig +short api.$DOMAIN @$IP | tail -1)

    if [ "$RESULT" == "$SERVER_IP" ]; then
        echo "   ✅ $NAME ($IP): Working"
    else
        echo "   ❌ $NAME ($IP): Not propagated yet"
    fi
done
echo ""

# Summary and recommendations
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$WILDCARD_WORKS" = true ]; then
    echo "✅ WILDCARD DNS IS WORKING!"
    echo ""
    echo "🎯 Next step: Run SSL certificate script"
    echo "   cd /Users/jamessunheart/Development/SERVICES"
    echo "   ./get-ssl-certs.sh"
    echo ""
else
    echo "❌ WILDCARD DNS NOT YET PROPAGATED"
    echo ""
    echo "🔧 Troubleshooting:"
    echo ""
    echo "1. Check DNS provider dashboard:"
    echo "   - Verify wildcard record exists: * → $SERVER_IP"
    echo "   - Check for conflicting specific records (api, match, etc.)"
    echo "   - Lower TTL to 300 seconds for faster propagation"
    echo ""
    echo "2. Wait for propagation:"
    echo "   - Can take 5 minutes to 48 hours"
    echo "   - Check status: https://dnschecker.org"
    echo ""
    echo "3. Clear DNS cache:"
    echo "   - Mac: sudo dscacheutil -flushcache"
    echo "   - Linux: sudo systemd-resolve --flush-caches"
    echo ""
    echo "4. Verify wildcard syntax at your DNS provider:"
    echo "   - Some providers want: *"
    echo "   - Others want: *.fullpotential.com"
    echo "   - Check their documentation"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
