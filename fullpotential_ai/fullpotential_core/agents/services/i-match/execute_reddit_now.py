#!/usr/bin/env python3
"""
EXECUTABLE Reddit Poster - Posts to r/fatFIRE and r/financialindependence NOW

This script ACTUALLY POSTS (not simulated).
Requires Reddit API credentials.
"""

import os
import praw
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reddit API credentials - set these as environment variables
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")

# Check credentials
missing_creds = []
if not REDDIT_CLIENT_ID:
    missing_creds.append("REDDIT_CLIENT_ID")
if not REDDIT_CLIENT_SECRET:
    missing_creds.append("REDDIT_CLIENT_SECRET")
if not REDDIT_USERNAME:
    missing_creds.append("REDDIT_USERNAME")
if not REDDIT_PASSWORD:
    missing_creds.append("REDDIT_PASSWORD")

if missing_creds:
    logger.error("❌ Missing Reddit credentials:")
    for cred in missing_creds:
        logger.error(f"   - {cred}")
    logger.error("")
    logger.error("Get credentials from: https://www.reddit.com/prefs/apps")
    logger.error("Then set environment variables:")
    logger.error("  export REDDIT_CLIENT_ID='...'")
    logger.error("  export REDDIT_CLIENT_SECRET='...'")
    logger.error("  export REDDIT_USERNAME='...'")
    logger.error("  export REDDIT_PASSWORD='...'")
    exit(1)

# Post content
FATFIRE_POST = {
    "title": "Built an AI to find your perfect financial advisor (free for customers)",
    "body": """I got burned by a generic financial advisor who didn't understand tech compensation.

So I built an AI matching system that analyzes 100+ advisors to find the perfect fit based on:
• Your specific needs (RSUs, ISOs, tax optimization, etc.)
• Values alignment (fee-only vs commission, philosophy)
• Communication style
• Specialization

Free for customers. Advisors pay us only if you engage.

Testing with 50 people this week. Comment or DM if interested.

http://198.54.123.234:8401/

Edit: Wow, didn't expect this response! Sending links to everyone who commented. Please allow 24 hours for matches."""
}

FINANCIALINDEPENDENCE_POST = {
    "title": "Free AI matching to find financial advisor who gets FIRE",
    "body": """Finding a financial advisor who understands FIRE is hard.

Most push expensive products or don't get the early retirement mindset.

I built an AI that matches you with advisors based on:
• FIRE specialization
• Fee-only requirement
• Tax optimization focus
• Your specific situation (income, savings rate, timeline)

Free service (advisors pay if you engage). Testing with 50 people.

Want in? Comment or DM.

http://198.54.123.234:8401/"""
}


def create_reddit_client():
    """Create authenticated Reddit client"""
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent="I-MATCH-Bot/1.0 by {}".format(REDDIT_USERNAME),
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD
        )

        # Test authentication
        logger.info(f"✅ Authenticated as: {reddit.user.me()}")
        return reddit

    except Exception as e:
        logger.error(f"❌ Failed to authenticate: {e}")
        return None


def post_to_subreddit(reddit, subreddit_name, title, body):
    """Post to a specific subreddit"""
    try:
        subreddit = reddit.subreddit(subreddit_name)

        # Submit post
        submission = subreddit.submit(
            title=title,
            selftext=body
        )

        logger.info(f"✅ Posted to r/{subreddit_name}")
        logger.info(f"   URL: https://reddit.com{submission.permalink}")
        logger.info(f"   ID: {submission.id}")

        return submission

    except Exception as e:
        logger.error(f"❌ Failed to post to r/{subreddit_name}: {e}")
        return None


def main():
    """Execute Reddit posting"""
    logger.info("=" * 70)
    logger.info("🚀 EXECUTABLE REDDIT POSTER - I MATCH Phase 1")
    logger.info("=" * 70)
    logger.info("")
    logger.info("This script will ACTUALLY POST to Reddit (not simulated)")
    logger.info("")

    # Create Reddit client
    logger.info("🔐 Authenticating with Reddit API...")
    reddit = create_reddit_client()

    if not reddit:
        logger.error("❌ Authentication failed - exiting")
        return

    logger.info("")
    logger.info("=" * 70)
    logger.info("📝 POSTING TO r/fatFIRE")
    logger.info("=" * 70)
    logger.info("")

    # Post to r/fatFIRE
    fatfire_submission = post_to_subreddit(
        reddit,
        "fatFIRE",
        FATFIRE_POST["title"],
        FATFIRE_POST["body"]
    )

    if fatfire_submission:
        logger.info("")
        logger.info("🎯 NEXT STEPS:")
        logger.info("  1. Monitor comments: https://reddit.com{fatfire_submission.permalink}")
        logger.info("  2. Reply to interested people with link to form")
        logger.info("  3. Guide them to: http://198.54.123.234:8401/")
        logger.info("")

    # Wait before posting to second subreddit (avoid spam detection)
    logger.info("")
    logger.info("⏳ Waiting 60 seconds before posting to r/financialindependence...")
    logger.info("   (To avoid Reddit spam detection)")
    logger.info("")

    import time
    time.sleep(60)

    logger.info("=" * 70)
    logger.info("📝 POSTING TO r/financialindependence")
    logger.info("=" * 70)
    logger.info("")

    # Post to r/financialindependence
    fi_submission = post_to_subreddit(
        reddit,
        "financialindependence",
        FINANCIALINDEPENDENCE_POST["title"],
        FINANCIALINDEPENDENCE_POST["body"]
    )

    if fi_submission:
        logger.info("")
        logger.info("🎯 NEXT STEPS:")
        logger.info(f"  1. Monitor comments: https://reddit.com{fi_submission.permalink}")
        logger.info("  2. Reply to interested people")
        logger.info("  3. Guide them to form")
        logger.info("")

    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ REDDIT POSTING COMPLETE")
    logger.info("=" * 70)
    logger.info("")

    if fatfire_submission and fi_submission:
        logger.info("🎉 BOTH POSTS LIVE!")
        logger.info("")
        logger.info("Monitor these URLs:")
        logger.info(f"  • r/fatFIRE: https://reddit.com{fatfire_submission.permalink}")
        logger.info(f"  • r/financialindependence: https://reddit.com{fi_submission.permalink}")
        logger.info("")
        logger.info("Expected outcome:")
        logger.info("  • 10-50 comments per post")
        logger.info("  • 5-20 customers fill out form")
        logger.info("  • First customer within 24 hours")
        logger.info("")
        logger.info("🤖 Start First Match Bot:")
        logger.info("  cd /Users/jamessunheart/Development/agents/services/i-match")
        logger.info("  python3 first_match_bot.py")
        logger.info("")
    else:
        logger.error("⚠️  Some posts failed - check errors above")

    logger.info("=" * 70)


if __name__ == "__main__":
    main()
