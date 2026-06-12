#!/bin/bash
# ============================================
# Ad Portal - Add Credentials
# ============================================
# 
# Usage: Run on server after getting credentials from assistant
#   ./add-credentials.sh
#
# ============================================

set -e

ENV_FILE="/opt/fpai/services/ad-portal/.env"

echo "📡 Ad Portal Credential Setup"
echo "=============================="
echo ""

# Meta credentials
read -p "META_APP_ID: " META_APP_ID
read -p "META_APP_SECRET: " META_APP_SECRET
read -p "META_ACCESS_TOKEN: " META_ACCESS_TOKEN
read -p "META_AD_ACCOUNT_ID (starts with act_): " META_AD_ACCOUNT_ID
read -p "META_PIXEL_ID: " META_PIXEL_ID

# Stripe credentials
read -p "STRIPE_SECRET_KEY (starts with sk_): " STRIPE_SECRET_KEY
read -p "STRIPE_WEBHOOK_SECRET (starts with whsec_): " STRIPE_WEBHOOK_SECRET

echo ""
echo "📝 Updating $ENV_FILE..."

# Update the .env file
cat > $ENV_FILE << EOF
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ad_portal

# Meta Ads
META_APP_ID=$META_APP_ID
META_APP_SECRET=$META_APP_SECRET
META_ACCESS_TOKEN=$META_ACCESS_TOKEN
META_AD_ACCOUNT_ID=$META_AD_ACCOUNT_ID
META_PIXEL_ID=$META_PIXEL_ID

# Stripe
STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET

# UC Credits Gateway
UC_GATEWAY_URL=http://localhost:8765

# AI Brain
AI_BRAIN_URL=http://162.0.208.88:8101

# Service
PORT=8850
EOF

echo "✅ Credentials saved!"
echo ""
echo "🔄 Restarting ad-portal service..."
systemctl restart ad-portal

sleep 3

echo ""
echo "🧪 Testing..."
curl -s http://localhost:8850/health
echo ""
echo ""
echo "✅ Done! Ad Portal is configured and running."
echo ""
echo "Next: Create your first offer at https://fullpotential.ai/ads/api/offers"


