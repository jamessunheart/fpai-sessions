#!/bin/bash

echo "🚀 White Rock Ministry Landing Page - Quick Deploy"
echo "=================================================="
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
fi

echo "✅ Vercel CLI ready"
echo ""
echo "🌐 Deploying to Vercel..."
echo ""

cd "$(dirname "$0")"
vercel --prod

echo ""
echo "=================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Set up Stripe payment links:"
echo "   → https://dashboard.stripe.com/products"
echo "   → Create 3 products: $2,500 / $7,500 / $15,000"
echo "   → Copy payment links"
echo ""
echo "2. Set up Calendly:"
echo "   → https://calendly.com"
echo "   → Create 90-min consultation event"
echo "   → Copy booking link"
echo ""
echo "3. Update landing page with links"
echo "4. Redeploy: vercel --prod"
echo ""
echo "5. Launch Facebook ads ($100/week budget)"
echo ""
echo "📖 See DEPLOY.md for detailed instructions"
echo "=================================================="
