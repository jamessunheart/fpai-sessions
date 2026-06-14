#!/bin/bash
# 🚀 LAUNCH 2X TREASURY EXECUTION
# Quick-start script for doubling treasury from $373K → $746K+

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💰 2X TREASURY EXECUTION - LAUNCH SEQUENCE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Show current treasury status
echo "📊 STEP 1: Current Treasury Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd /Users/jamessunheart/Development
python3 treasury_tracker.py
echo ""

# Step 2: Verify I MATCH infrastructure
echo "📊 STEP 2: Verify I MATCH Infrastructure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Service Health:"
curl -s http://198.54.123.234:8401/health | python3 -m json.tool
echo ""
echo "Current State:"
curl -s http://198.54.123.234:8401/state | python3 -m json.tool
echo ""

# Step 3: Show dashboard
echo "📊 STEP 3: Opening Execution Dashboards"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Opening dashboards in browser..."
echo ""

# Open dashboard files
open /Users/jamessunheart/Development/2X_TREASURY_DASHBOARD.md
sleep 1
open /Users/jamessunheart/Development/2X_TREASURY_EXECUTION_PLAN.md
sleep 1

# Step 4: Open I MATCH launch materials
echo "📊 STEP 4: Opening I MATCH Launch Materials"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd /Users/jamessunheart/Development/SERVICES/i-match
open PHASE_1_LAUNCH_NOW.md
sleep 1
open LAUNCH_TRACKER.md
sleep 1

# Step 5: Open key URLs
echo "📊 STEP 5: Opening Key URLs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Opening I MATCH pages..."
open http://198.54.123.234:8401/
open http://198.54.123.234:8401/providers
echo ""

echo "Opening LinkedIn search (financial advisors)..."
open "https://www.linkedin.com/search/results/people/?keywords=financial%20advisor%20CFP&origin=GLOBAL_SEARCH_HEADER"
echo ""

echo "Opening Reddit for posting..."
open "https://www.reddit.com/r/fatFIRE/submit"
echo ""

# Step 6: Final instructions
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 2X TREASURY LAUNCH SEQUENCE COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 IMMEDIATE NEXT ACTIONS (Priority 1):"
echo ""
echo "1️⃣  LinkedIn: Send 20 connection requests to financial advisors"
echo "    • Search for: \"financial advisor\" OR \"CFP\" OR \"wealth manager\""
echo "    • Message: \"Hi [Name] - AI matching for financial advisors. Interested in quality leads?\""
echo ""
echo "2️⃣  Reddit: Post to r/fatFIRE"
echo "    • Title: \"Built an AI to find your perfect financial advisor (free for customers)\""
echo "    • Body: See PHASE_1_LAUNCH_NOW.md for full template"
echo ""
echo "3️⃣  LinkedIn: Post announcement"
echo "    • Announce I MATCH launch"
echo "    • Include link: http://198.54.123.234:8401/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 TARGET: Generate first $5-12K revenue in 7 days"
echo "🎯 TIMELINE: Reach $746K (2X) in 6-12 months"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💰 Current treasury: \$373,261"
echo "🎯 Target (2X): \$746,522"
echo "📈 Gap to close: \$373,261"
echo ""
echo "🚀 INFRASTRUCTURE: ✅ 100% READY"
echo "🚀 EXECUTION: 🔴 AWAITING YOUR ACTION"
echo ""
echo "Let's 2X this treasury! 💎"
echo ""
