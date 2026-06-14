#!/bin/bash
# ONE-COMMAND EXECUTION for I MATCH Phase 1 Launch
# This script makes it TRIVIAL to execute

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "🚀 I MATCH PHASE 1 EXECUTION - ONE COMMAND LAUNCH"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "This script will help you execute Phase 1 in ONE SESSION."
echo ""
echo "You can choose:"
echo "  1. Reddit posting (EASIEST - 2 minutes)"
echo "  2. LinkedIn automation (MEDIUM - 5 minutes setup + 10 min execution)"
echo "  3. Both (RECOMMENDED - 15 minutes total)"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Check if we're in the right directory
if [ ! -f "execute_reddit_now.py" ]; then
    echo "❌ Error: Must run from /agents/services/i-match directory"
    echo ""
    echo "Run this command first:"
    echo "  cd /Users/jamessunheart/Development/agents/services/i-match"
    exit 1
fi

# Menu
echo "Choose execution method:"
echo ""
echo "  1) Reddit only (easiest, no credentials needed if posting manually)"
echo "  2) LinkedIn only (requires LinkedIn login)"
echo "  3) Both Reddit + LinkedIn (recommended)"
echo "  4) Just show me what to do (no execution)"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "═══════════════════════════════════════════════════════════════════"
        echo "📝 REDDIT EXECUTION"
        echo "═══════════════════════════════════════════════════════════════════"
        echo ""

        # Check if credentials are set
        if [ -z "$REDDIT_CLIENT_ID" ]; then
            echo "⚠️  Reddit API credentials not set"
            echo ""
            echo "OPTION A: Set credentials and auto-post"
            echo "  1. Go to: https://www.reddit.com/prefs/apps"
            echo "  2. Create app (type: script)"
            echo "  3. Set environment variables:"
            echo "     export REDDIT_CLIENT_ID='...'"
            echo "     export REDDIT_CLIENT_SECRET='...'"
            echo "     export REDDIT_USERNAME='...'"
            echo "     export REDDIT_PASSWORD='...'"
            echo "  4. Run: python3 execute_reddit_now.py"
            echo ""
            echo "OPTION B: Manual post (FASTEST - 2 minutes)"
            echo "  1. Open: https://reddit.com/r/fatFIRE"
            echo "  2. Click 'Create Post'"
            echo "  3. Copy title from: CUSTOMER_ACQUISITION_SCRIPT.md"
            echo "  4. Copy body from: CUSTOMER_ACQUISITION_SCRIPT.md"
            echo "  5. Click 'Post'"
            echo ""
            read -p "Press ENTER to see the post content..."
            echo ""
            cat CUSTOMER_ACQUISITION_SCRIPT.md | head -30
            echo ""
        else
            echo "✅ Reddit credentials found - executing auto-post..."
            python3 execute_reddit_now.py
        fi
        ;;

    2)
        echo ""
        echo "═══════════════════════════════════════════════════════════════════"
        echo "💼 LINKEDIN EXECUTION"
        echo "═══════════════════════════════════════════════════════════════════"
        echo ""

        # Check if credentials are set
        if [ -z "$LINKEDIN_EMAIL" ] || [ -z "$LINKEDIN_PASSWORD" ]; then
            echo "📋 LinkedIn credentials needed"
            echo ""
            read -p "LinkedIn Email: " linkedin_email
            read -sp "LinkedIn Password: " linkedin_password
            echo ""
            echo ""

            export LINKEDIN_EMAIL="$linkedin_email"
            export LINKEDIN_PASSWORD="$linkedin_password"
        fi

        echo "Running LinkedIn automation in DRY RUN mode first..."
        echo "(This shows you what it would do without actually sending)"
        echo ""
        python3 execute_linkedin_now.py --dry-run

        echo ""
        read -p "Run in LIVE mode? (sends real connections) [y/N]: " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            echo ""
            echo "🚨 Running in LIVE mode - sending real connections..."
            python3 execute_linkedin_now.py --live
        else
            echo "❌ Cancelled - no connections sent"
        fi
        ;;

    3)
        echo ""
        echo "═══════════════════════════════════════════════════════════════════"
        echo "🚀 FULL EXECUTION - REDDIT + LINKEDIN"
        echo "═══════════════════════════════════════════════════════════════════"
        echo ""
        echo "This will:"
        echo "  1. Post to r/fatFIRE and r/financialindependence"
        echo "  2. Send LinkedIn connection requests to 10 financial advisors"
        echo ""
        read -p "Continue? [y/N]: " confirm

        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            echo "❌ Cancelled"
            exit 0
        fi

        # Reddit first
        echo ""
        echo "STEP 1: Reddit Posting"
        echo "----------------------"

        if [ -z "$REDDIT_CLIENT_ID" ]; then
            echo "Manual posting needed (see CUSTOMER_ACQUISITION_SCRIPT.md)"
            echo ""
            read -p "Press ENTER when Reddit posts are live..."
        else
            python3 execute_reddit_now.py
        fi

        # LinkedIn second
        echo ""
        echo "STEP 2: LinkedIn Automation"
        echo "---------------------------"

        if [ -z "$LINKEDIN_EMAIL" ]; then
            read -p "LinkedIn Email: " linkedin_email
            read -sp "LinkedIn Password: " linkedin_password
            echo ""
            export LINKEDIN_EMAIL="$linkedin_email"
            export LINKEDIN_PASSWORD="$linkedin_password"
        fi

        python3 execute_linkedin_now.py --live
        ;;

    4)
        echo ""
        echo "═══════════════════════════════════════════════════════════════════"
        echo "📖 EXECUTION GUIDE"
        echo "═══════════════════════════════════════════════════════════════════"
        echo ""
        echo "Read the detailed guide:"
        echo "  cat EXECUTE_FIRST_MATCH_NOW.md"
        echo ""
        echo "Or just:"
        echo ""
        echo "REDDIT (2 minutes):"
        echo "  1. Go to https://reddit.com/r/fatFIRE"
        echo "  2. Copy/paste from CUSTOMER_ACQUISITION_SCRIPT.md"
        echo "  3. Post"
        echo ""
        echo "LINKEDIN (15 minutes):"
        echo "  1. Search: 'financial advisor CFP San Francisco'"
        echo "  2. Send connection: 'Hi [Name] - Quick question about quality leads'"
        echo "  3. When accepted, DM template in EXECUTE_FIRST_MATCH_NOW.md"
        echo ""
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ EXECUTION COMPLETE"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "🎯 NEXT STEPS:"
echo ""
echo "1. Start First Match Bot to monitor signups:"
echo "   python3 first_match_bot.py"
echo ""
echo "2. Monitor for customer/provider signups:"
echo "   watch -n 10 'sqlite3 i_match.db \"SELECT COUNT(*) FROM customers\"'"
echo ""
echo "3. When you have 1 customer + 1 provider:"
echo "   Bot auto-creates match and generates introduction email"
echo ""
echo "4. Send introduction email from FIRST_MATCH_ALERT.txt"
echo ""
echo "Expected timeline:"
echo "  • Hour 0-12: Signups come in"
echo "  • Hour 12: Bot creates first match"
echo "  • Day 1-3: Introduction call scheduled"
echo "  • Day 7-14: Customer engages provider"
echo "  • Day 30-60: First commission (\$500-2,500)"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""
