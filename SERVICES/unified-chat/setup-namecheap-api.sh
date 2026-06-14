#!/bin/bash
# One-time setup for Namecheap API automation

echo "🔐 Namecheap API Setup - One Time Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This enables automated DNS management for all future subdomains."
echo ""

# Get current IP
CURRENT_IP=$(curl -s https://api.ipify.org)
echo "📍 Your current IP: $CURRENT_IP"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Enable API Access"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Open: https://ap.www.namecheap.com/settings/tools/apiaccess/"
echo "2. Click 'Enable API Access' (if not already enabled)"
echo "3. Accept the terms"
echo ""
read -p "Press ENTER when API access is enabled..."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Whitelist Your IP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "On the same page, add this IP to the whitelist:"
echo ""
echo "  $CURRENT_IP"
echo ""
echo "Click 'Add' next to the IP whitelist section."
echo ""
read -p "Press ENTER when IP is whitelisted..."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Get Your Credentials"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "You should see on that page:"
echo "  - API Key (long string)"
echo "  - Username"
echo ""

read -p "Enter your Namecheap username: " NC_USER
read -p "Enter your Namecheap API key: " NC_KEY
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Storing Credentials Securely"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Store in credential vault
cd /Users/jamessunheart/Development/docs/coordination

if [ -f ./scripts/session-set-credential.sh ]; then
    echo "Storing in encrypted credential vault..."
    ./scripts/session-set-credential.sh NAMECHEAP_API_USER "$NC_USER" "api_credentials"
    ./scripts/session-set-credential.sh NAMECHEAP_API_KEY "$NC_KEY" "api_credentials"
    echo "✅ Credentials stored in vault"
else
    echo "Credential vault not available, storing in environment file..."
    cat > /Users/jamessunheart/Development/SERVICES/.namecheap-credentials << EOF
export NAMECHEAP_API_USER="$NC_USER"
export NAMECHEAP_API_KEY="$NC_KEY"
export NAMECHEAP_USERNAME="$NC_USER"
EOF
    chmod 600 /Users/jamessunheart/Development/SERVICES/.namecheap-credentials
    echo "✅ Credentials stored in .namecheap-credentials"
fi

# Also set for current session
export NAMECHEAP_API_USER="$NC_USER"
export NAMECHEAP_API_KEY="$NC_KEY"
export NAMECHEAP_USERNAME="$NC_USER"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Testing API Access"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test by adding chat subdomain
cd /Users/jamessunheart/Development/SERVICES
./namecheap-dns-automation.sh add chat

if [ $? -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ SUCCESS! API is configured and working!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🎉 You can now automate DNS for any future subdomain!"
    echo ""
    echo "Examples:"
    echo "  ./namecheap-dns-automation.sh add api"
    echo "  ./namecheap-dns-automation.sh add dashboard"
    echo "  ./namecheap-dns-automation.sh add anything"
    echo ""
    echo "⏳ DNS propagation: Wait ~5-10 minutes, then run:"
    echo "   cd /Users/jamessunheart/Development/SERVICES/unified-chat"
    echo "   ./setup-domain.sh"
    echo ""
else
    echo ""
    echo "❌ API test failed. Please check:"
    echo "  - API access is enabled"
    echo "  - IP $CURRENT_IP is whitelisted"
    echo "  - Username and API key are correct"
    echo ""
fi
