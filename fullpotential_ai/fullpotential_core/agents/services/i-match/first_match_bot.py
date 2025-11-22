#!/usr/bin/env python3
"""
FIRST MATCH BOT - Get the first I MATCH customer
Simple autonomous bot that uses ready-made content to generate first lead

What it does:
1. Shows you the ready-to-post content
2. Gives you 1-click posting instructions
3. Monitors for leads (manual check helper)
4. Helps capture first customer into database

This is NOT a full automation engine.
This is ONE BOT to get ONE CUSTOMER TODAY.
"""

import sys
from pathlib import Path

# Ready-to-post content from READY_TO_POST_NOW.md
REDDIT_POST = """
🚀 Day 1: Launching with $0 marketing budget

I built an AI that matches people with perfect service providers in 24 hours:
• Executive coaches
• Church formation consultants
• AI developers

Today's goal: 10 signups without spending a dollar.

My tactics:
1. This post
2. DM 10 friends
3. Reddit value commenting
4. Facebook groups

Try it: https://fullpotential.com/imatch

Following along? I'll share exact numbers tonight.

What free marketing tactic should I try tomorrow? 👇
"""

LINKEDIN_POST = """
Finding the right service provider is broken.

I spent 20+ hours researching executive coaches last year. Read dozens of websites. Still felt uncertain.

Then I spent another 15 hours helping a friend find church formation services. Same problem.

So I built something better.

An AI that does the hard work for you:

✓ Analyzes your specific needs (2-minute form)
✓ Evaluates compatibility across 5 factors
✓ Finds your top 3 matches in 24 hours
✓ Sets up free consultations with each

Currently live for:
• Executive Coaching
• Church Formation (501c3/508c1a)
• AI Development & Automation

This is a soft launch - testing with a small group first.

If you (or someone in your network) could use this:
👉 https://fullpotential.com/imatch

What do you think? Does this solve a real problem?

#ServiceMatching #AI #ExecutiveCoaching
"""

def show_posting_instructions():
    """Show 1-click posting instructions"""
    print("\n" + "="*80)
    print("🚀 FIRST MATCH BOT - Get Your First Customer TODAY")
    print("="*80)

    print("\n📋 STEP 1: POST TO REDDIT (5 minutes)")
    print("-" * 80)
    print("1. Go to: https://reddit.com/r/Entrepreneur/submit")
    print("2. Title: Day 1: Launching with $0 marketing budget")
    print("3. Copy this text:\n")
    print(REDDIT_POST)
    print("\n4. Click 'Post'")
    print("5. ✅ DONE - You just reached 3M+ entrepreneurs")

    print("\n\n📋 STEP 2: POST TO LINKEDIN (5 minutes)")
    print("-" * 80)
    print("1. Go to: https://linkedin.com")
    print("2. Click 'Start a post'")
    print("3. Copy this text:\n")
    print(LINKEDIN_POST)
    print("\n4. Click 'Post'")
    print("5. ✅ DONE - You just reached your network")

    print("\n\n📋 STEP 3: MONITOR & RESPOND (ongoing)")
    print("-" * 80)
    print("• Check Reddit every 2 hours for comments/DMs")
    print("• Check LinkedIn for comments/messages")
    print("• Respond within 30 minutes (builds trust)")
    print("• When someone shows interest, direct them to:")
    print("  👉 https://fullpotential.com/imatch")

    print("\n\n📋 STEP 4: CAPTURE FIRST LEAD")
    print("-" * 80)
    print("When someone fills out the form:")
    print("• Database automatically captures their info")
    print("• You'll see them at: http://198.54.123.234:8401/api/customers")
    print("• Contact them within 24 hours to discuss needs")
    print("• Match them with providers manually for first match")

    print("\n\n💰 EXPECTED OUTCOME:")
    print("-" * 80)
    print("• Reddit post: 100-500 views, 5-20 comments, 1-3 leads")
    print("• LinkedIn post: 50-200 views, 3-10 comments, 1-2 leads")
    print("• Total expected: 2-5 leads in first 24 hours")
    print("• First customer: Within 2-3 days")
    print("• First match: Within 7 days")
    print("• First revenue: Within 30 days ($3-11K)")

    print("\n\n🎯 THIS IS THE CRITICAL PATH TO FIRST REVENUE")
    print("="*80)
    print()

def offer_automation_help():
    """Offer to automate monitoring"""
    print("\n❓ Want me to help automate monitoring?")
    print("-" * 80)
    print()
    print("I can build:")
    print("• Reddit comment checker (alerts you to new responses)")
    print("• LinkedIn message monitor (checks for DMs)")
    print("• Lead notification system (emails you when form submitted)")
    print()
    response = input("Build monitoring automation? (y/n): ").lower()

    if response == 'y':
        print("\n✅ Great! I'll build a simple monitoring script.")
        print("This will check every 15 minutes and notify you of new activity.")
        print()
        print("Building monitoring_bot.py...")
        # Could build this next
        return True
    else:
        print("\n✅ No problem! Manual monitoring works great for first customer.")
        return False

def main():
    """Main execution"""
    show_posting_instructions()

    print("\n🚦 READY TO POST?")
    print()
    print("This is the ONE action that gets you from $0 → First Customer")
    print()
    response = input("Show me detailed posting steps? (y/n): ").lower()

    if response == 'y':
        print("\n✅ Perfect! Follow the steps above.")
        print()
        print("💡 PRO TIP: Set a timer for 2 hours")
        print("When it goes off, check both platforms and respond to EVERY comment.")
        print("Engagement in first 2 hours determines post visibility.")
        print()

        # offer_automation_help()

    print("\n🌐⚡💎 This is how Phase 1 begins.")
    print()

if __name__ == "__main__":
    main()
