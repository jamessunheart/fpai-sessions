#!/bin/bash
# =============================================================================
# 💰 REVENUE ACTIVATION SCRIPT
# =============================================================================
# Run this to check and activate all revenue streams
# Usage: ./scripts/activate-revenue-streams.sh

set -e

echo "🚀 FULL POTENTIAL REVENUE ACTIVATION ENGINE"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local name=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo -e "  ✅ ${GREEN}$name${NC}: ONLINE"
        return 0
    else
        echo -e "  ❌ ${RED}$name${NC}: OFFLINE ($response)"
        return 1
    fi
}

echo -e "${CYAN}📊 CHECKING REVENUE SERVICES...${NC}"
echo ""

# Check all revenue services
check_service "WhaleTrack Trading" "http://198.54.123.234:8600/health"
check_service "I-MATCH" "http://198.54.123.234:8401/health"
check_service "AI Automation" "http://198.54.123.234:8750/health"
check_service "Credits Gateway" "http://198.54.123.234:8765/health"
check_service "AI Brain" "http://162.0.208.88:8101/health"

echo ""
echo -e "${CYAN}💳 PAYMENT LINKS (Ready to Share):${NC}"
echo ""
echo -e "  ${GREEN}AI Employee ($1,500/mo):${NC}"
echo "    https://buy.stripe.com/6oU5kCesF2xncRnePj9R608"
echo ""
echo -e "  ${GREEN}AI Team ($3,500/mo):${NC}"
echo "    https://buy.stripe.com/5kQcN470d0pf2cJ4aF9R609"
echo ""
echo -e "  ${GREEN}AI Department ($7,500/mo):${NC}"
echo "    https://buy.stripe.com/8x27sK98l0pf5oVcHb9R60a"
echo ""
echo -e "  ${YELLOW}50% Pilot Coupon:${NC} wIhS3yUL"
echo ""

echo -e "${CYAN}🔗 AFFILIATE PROGRAM SIGNUP LINKS:${NC}"
echo ""
echo "  1. Mindvalley (30-40% commission): https://www.mindvalley.com/affiliates"
echo "  2. Kajabi (30% recurring): https://kajabi.com/affiliates"
echo "  3. ClickFunnels (40% recurring): https://www.clickfunnels.com/affiliates"
echo "  4. ConvertKit (30% recurring): https://convertkit.com/ambassador"
echo "  5. Athletic Greens ($30-100/sale): https://athleticgreens.com/partnerships"
echo ""

echo -e "${CYAN}📱 DASHBOARD URLS:${NC}"
echo ""
echo "  WhaleTrack: http://198.54.123.234:8600/dashboard"
echo "  I-MATCH: http://198.54.123.234:8401/"
echo "  God Mode: https://fullpotential.ai/admin/godmode"
echo ""

echo -e "${CYAN}🐋 WHALETRACK LIVE TRADING STATUS:${NC}"
echo ""

# Get WhaleTrack live status (requires auth but we can check if endpoints exist)
LIVE_STATUS=$(curl -s "http://198.54.123.234:8600/api/live/status" 2>/dev/null)
if echo "$LIVE_STATUS" | grep -q "user_id"; then
    echo -e "  ${GREEN}Live trading endpoints: READY${NC}"
    echo "  Access via dashboard to configure credentials and go live"
else
    echo -e "  ${YELLOW}Live trading: Authentication required${NC}"
    echo "  Go to dashboard → Portfolio → Configure Hyperliquid"
fi

echo ""
echo -e "${CYAN}📋 TODAY'S ACTION ITEMS:${NC}"
echo ""
echo "  [ ] 1. Login to WhaleTrack dashboard and activate live trading"
echo "  [ ] 2. Sign up for Mindvalley affiliate (5 min)"
echo "  [ ] 3. Sign up for Kajabi affiliate (5 min)"
echo "  [ ] 4. Post AI Automation on LinkedIn"
echo "  [ ] 5. Share I-MATCH with 3 service providers"
echo ""

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}Revenue Potential if ALL activated: \$58K-\$270K/month${NC}"
echo -e "${GREEN}Current Revenue: \$0 (nothing activated yet!)${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""

# Open affiliate signup URLs (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}Opening affiliate signup URLs in browser...${NC}"
    read -p "Press Enter to open affiliate signup pages (or Ctrl+C to skip)" 
    open "https://www.mindvalley.com/affiliates"
    sleep 1
    open "https://kajabi.com/affiliates"
    sleep 1
    open "https://www.clickfunnels.com/affiliates"
fi

echo ""
echo "Done! Check REVENUE_PERFECTION_ENGINE.md for full strategy."







