#!/bin/bash

# 💰 GUMROAD UPLOAD HELPER
# Generates copy-paste ready product descriptions for Gumroad

echo "💰 GUMROAD PRODUCT UPLOAD HELPER"
echo "=================================="
echo ""
echo "Select product to upload:"
echo ""
echo "1. Crypto Portfolio Tracker (\$49)"
echo "2. Multi-Session AI Coordinator (\$79)"
echo "3. AI Automation Playbook (\$39)"
echo "4. Treasury Management System (\$129)"
echo "5. Dashboard Collection (\$99)"
echo "6. Automation Scripts (\$29)"
echo "7. FULL BUNDLE (\$199) ⭐ RECOMMENDED"
echo "8. ALL PRODUCTS (upload all 7)"
echo ""

read -p "Choose (1-8): " choice

case $choice in
    1)
        echo ""
        echo "📦 PRODUCT: Crypto Portfolio Tracker"
        echo "💰 PRICE: \$49"
        echo ""
        echo "=== COPY THIS FOR GUMROAD TITLE ==="
        echo "Crypto Portfolio Tracker - Track \$100K+ Like a Pro"
        echo ""
        echo "=== COPY THIS FOR GUMROAD DESCRIPTION ==="
        cat <<'EOF'
**Track your crypto portfolio like a $354K professional trader**

🎯 What You Get:
• Real-time P&L calculations across all positions
• Liquidation risk monitoring for leveraged trades
• Multi-wallet consolidation (spot + leveraged)
• Professional FastAPI dashboard
• 15-minute setup with clear documentation

💎 Perfect For:
✓ Crypto traders managing $10K+ portfolios
✓ Anyone with leveraged positions (2x, 3x, etc.)
✓ Traders who want professional-grade tracking
✓ People tired of spreadsheets

📦 Includes:
- Complete Python/FastAPI application
- Professional dashboard UI
- Example configurations
- Quick start guide
- MIT License (commercial use OK)

⚡ Setup Time: 15 minutes
🔧 Requirements: Python 3.8+, basic terminal knowledge

🛡️ 30-Day Money-Back Guarantee
If you can't get it running or it doesn't meet your needs, full refund. No questions asked.

Built by a trader, for traders. This is the actual system managing my $354K portfolio.

**Download, configure, and track your crypto like a pro in under 20 minutes.**
EOF
        echo ""
        echo "=== FILE TO UPLOAD ==="
        echo "/Users/jamessunheart/Development/PRODUCTS/crypto-portfolio-tracker.tar.gz"
        ;;

    7)
        echo ""
        echo "📦 PRODUCT: Full Potential AI Empire Bundle ⭐"
        echo "💰 PRICE: \$199 (Save \$225)"
        echo ""
        echo "=== COPY THIS FOR GUMROAD TITLE ==="
        echo "Full Potential AI Empire - Complete Bundle (6 Tools)"
        echo ""
        echo "=== COPY THIS FOR GUMROAD DESCRIPTION ==="
        cat <<'EOF'
**$424 worth of production AI/crypto tools for $199**

🚀 What You Get - ALL 6 Tools:

1️⃣ **Crypto Portfolio Tracker** ($49 value)
   → Track unlimited portfolios with liquidation monitoring

2️⃣ **Multi-Session AI Coordinator** ($79 value)
   → Coordinate 12+ AI agents simultaneously

3️⃣ **AI Automation Playbook** ($39 value)
   → $0 → $120K MRR marketing roadmap + templates

4️⃣ **Treasury Management System** ($129 value)
   → Complete crypto treasury infrastructure

5️⃣ **Dashboard Collection** ($99 value)
   → 3 production-ready dashboards (save 40+ dev hours)

6️⃣ **Automation Scripts** ($29 value)
   → 20+ production DevOps scripts

💰 **Total Value: $424**
💰 **Bundle Price: $199**
💰 **You Save: $225 (53% off)**

---

🎯 **Who This Is For:**

✓ Crypto traders managing real money
✓ Developers building AI systems
✓ Founders who need to move fast
✓ Anyone tired of building from scratch

---

🔥 **Why This Works:**

⚡ **Production Ready** - Not tutorials. Actual working systems from a real business.

🚀 **Save Weeks** - 40+ hours of development work. Just download, configure, and run.

💎 **Battle Tested** - Managing real money. Coordinating real AI agents. Generating real revenue.

---

📦 **What's Included:**

• All 6 complete tools (779KB total)
• Full source code with MIT License
• Professional documentation
• Setup guides for each tool
• Example configurations
• Email support

---

⚡ **Setup:** 15-60 minutes per tool
🔧 **Requirements:** Python 3.8+, basic terminal knowledge

---

🛡️ **30-Day Money-Back Guarantee**

Try it for 30 days. If you can't get it running or it doesn't work as described, full refund. No questions asked.

---

**Built in 24 hours with Claude AI + human expertise.**

I spent $200 on Claude AI to build these systems. I needed to 2x that investment FAST. So I packaged everything I built into sellable products.

This is production code I'm using in my actual business:
- Managing $354K in crypto
- Coordinating 12 AI sessions
- Building revenue systems

No fluff. Just tools that work.

---

🚀 **Ready to build faster?**

Stop building from scratch. Start with production code.

**Download now and start shipping in minutes, not weeks.**
EOF
        echo ""
        echo "=== FILE TO UPLOAD ==="
        echo "/Users/jamessunheart/Development/PRODUCTS/FULL-POTENTIAL-EMPIRE-BUNDLE.tar.gz"
        ;;

    8)
        echo ""
        echo "🚀 UPLOAD ALL PRODUCTS MODE"
        echo ""
        echo "Go to https://gumroad.com/products/new"
        echo ""
        echo "Upload in this order (highest value first):"
        echo ""
        echo "1. FULL-POTENTIAL-EMPIRE-BUNDLE.tar.gz - \$199"
        echo "2. treasury-system-complete.tar.gz - \$129"
        echo "3. dashboard-collection.tar.gz - \$99"
        echo "4. multi-session-coordinator.tar.gz - \$79"
        echo "5. crypto-portfolio-tracker.tar.gz - \$49"
        echo "6. ai-automation-playbook.tar.gz - \$39"
        echo "7. automation-scripts.tar.gz - \$29"
        echo ""
        echo "💡 TIP: Start with #1 (bundle) to get to market fastest"
        echo ""
        ;;

    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "📋 NEXT STEPS:"
echo "1. Go to https://gumroad.com/products/new"
echo "2. Upload the file shown above"
echo "3. Copy/paste the title and description"
echo "4. Set the price"
echo "5. Add tag: ai-tools"
echo "6. Publish!"
echo "7. Copy your product URL"
echo "8. Share everywhere!"
echo ""
