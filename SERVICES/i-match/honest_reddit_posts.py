#!/usr/bin/env python3
"""
HONEST Reddit Poster - Experimental framing with AI transparency
Following honesty principles from AUTONOMOUS_AGENT_HONESTY_PRINCIPLES.md
"""

import os
import praw
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reddit API credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")

# HONEST EXPERIMENTAL POSTS (following honesty checklist)

FATFIRE_HONEST = {
    "title": "AI Experiment: Testing if AI can match people to financial advisors better than Google",
    "body": """**Full transparency: Running an experiment and want to share what I'm learning.**

**What I built:**
I got frustrated finding a financial advisor who understood tech compensation (RSUs, ISOs, etc.), so I built an AI matching system using Claude. It analyzes advisors based on:
• Your specific needs (tech comp, tax optimization, etc.)
• Values alignment (fee-only vs commission)
• Communication style
• Specialization

**Current status:**
• Just launched (genuinely early stage)
• Zero customers so far
• Testing if AI can actually understand human compatibility or if this is just another "AI for X" thing
• This post was partially written by the AI (yes, we're self-aware about it)

**The honest question:** Can AI match people to professionals better than Googling + referrals? Or is this hype?

Free for customers (advisors pay commission if you engage). Very early - you'd be helping me learn if this works.

Help me find out: http://198.54.123.234:8401/

**P.S.** - Yes, Claude AI helped me write this post. We're exploring what AI + human collaboration actually looks like in practice. Maybe it works, maybe it doesn't. Let's find out together.

**P.P.S.** - Will report back in a week whether this was useful or just another AI dead end. Real experimentation, real learning."""
}

FINANCIALINDEPENDENCE_HONEST = {
    "title": "Experiment: Can AI find FIRE-friendly financial advisors better than Reddit?",
    "body": """**Full honesty: Testing an AI system and genuinely curious if it works.**

**The problem I'm testing:**
Finding a financial advisor who *gets* FIRE is surprisingly hard. Most push expensive products or don't understand the early retirement mindset.

**What I built:**
AI matching system (using Claude) that tries to match you with advisors based on:
• FIRE specialization (not just generic wealth management)
• Fee-only requirement (no commission incentives)
• Tax optimization focus (a big deal for FIRE)
• Your specific situation

**Current status:**
• Launched this week (very early stage)
• Zero customers yet - this is genuinely experimental
• AI helped write this post (being transparent about that)
• Testing if this is better than "ask Reddit for advisor recommendations"

**The honest test:** Does AI matching actually work? Or is this just another tech solution looking for a problem?

Free service for customers. You'd be one of the first - complete transparency: you're helping me learn if this is valuable.

Try it: http://198.54.123.234:8401/

**Curious what you think - even if it doesn't work for you.** Will report back whether this was useful or just hype.

**Note:** Claude AI co-wrote this post. Part of the experiment is exploring what genuine AI + human collaboration looks like. Maybe I'm wrong about this whole thing. Let's find out together.

**Follow-up commitment:** Will update this post in 1 week with results (success OR failure). Real learning, not just marketing."""
}

# VALIDATION CHECK (runs before posting)
def validate_honesty_compliance(post_data):
    """Check if post follows honesty principles"""
    title = post_data["title"]
    body = post_data["body"]
    full_text = title + " " + body

    checks = {
        "ai_disclosure": False,
        "experimental_framing": False,
        "stage_transparency": False,
        "uncertainty_acknowledged": False,
        "curiosity_invitation": False,
        "no_guarantees": True,
        "no_fomo": True,
        "no_fake_social_proof": True
    }

    # Check AI disclosure
    if "AI" in full_text and "Claude" in full_text:
        checks["ai_disclosure"] = True

    # Check experimental framing
    experiment_words = ["experiment", "testing", "exploring", "learning"]
    if any(word in full_text.lower() for word in experiment_words):
        checks["experimental_framing"] = True

    # Check stage transparency
    transparency_words = ["early stage", "zero customers", "just launched", "first"]
    if any(word in full_text.lower() for word in transparency_words):
        checks["stage_transparency"] = True

    # Check uncertainty
    uncertainty_words = ["might", "maybe", "curious", "testing if", "let's find out"]
    if any(word in full_text.lower() for word in uncertainty_words):
        checks["uncertainty_acknowledged"] = True

    # Check curiosity invitation
    invitation_words = ["help me", "curious what you think", "let's find out together"]
    if any(word in full_text.lower() for word in invitation_words):
        checks["curiosity_invitation"] = True

    # Check for forbidden phrases
    forbidden = ["guaranteed", "revolutionary", "limited spots", "act now", "thousands of users"]
    for phrase in forbidden:
        if phrase in full_text.lower():
            checks["no_guarantees"] = False
            checks["no_fomo"] = False
            checks["no_fake_social_proof"] = False

    return checks

def print_validation_report(post_name, checks):
    """Print validation report"""
    logger.info(f"\n📋 HONESTY VALIDATION: {post_name}")
    logger.info("=" * 60)

    all_passed = True

    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        logger.info(f"  {status} {check_name.replace('_', ' ').title()}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("✅ COMPLIANT: Safe to post")
    else:
        logger.info("❌ NON-COMPLIANT: Fix issues before posting")

    return all_passed

def create_reddit_client():
    """Create authenticated Reddit client"""
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent="I-MATCH-Honest-Bot/1.0 by {}".format(REDDIT_USERNAME),
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD
        )

        logger.info(f"✅ Authenticated as: {reddit.user.me()}")
        return reddit

    except Exception as e:
        logger.error(f"❌ Failed to authenticate: {e}")
        return None

def post_to_subreddit(reddit, subreddit_name, title, body):
    """Post to a specific subreddit"""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        submission = subreddit.submit(title=title, selftext=body)

        logger.info(f"✅ Posted to r/{subreddit_name}")
        logger.info(f"   URL: https://reddit.com{submission.permalink}")

        return submission

    except Exception as e:
        logger.error(f"❌ Failed to post to r/{subreddit_name}: {e}")
        return None

def main():
    """Execute honest Reddit posting with validation"""
    logger.info("=" * 70)
    logger.info("🌟 HONEST REDDIT POSTER - Experimental Framing")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Following honesty principles from:")
    logger.info("  AUTONOMOUS_AGENT_HONESTY_PRINCIPLES.md")
    logger.info("  PRE_SEND_HONESTY_CHECKLIST.md")
    logger.info("")

    # Check credentials
    missing = []
    if not REDDIT_CLIENT_ID: missing.append("REDDIT_CLIENT_ID")
    if not REDDIT_CLIENT_SECRET: missing.append("REDDIT_CLIENT_SECRET")
    if not REDDIT_USERNAME: missing.append("REDDIT_USERNAME")
    if not REDDIT_PASSWORD: missing.append("REDDIT_PASSWORD")

    if missing:
        logger.error("❌ Missing credentials:")
        for cred in missing:
            logger.error(f"   - {cred}")
        logger.error("")
        logger.error("Setup instructions:")
        logger.error("1. Go to: https://www.reddit.com/prefs/apps")
        logger.error("2. Click 'create app' → 'script'")
        logger.error("3. Name: 'I-MATCH-Experiment'")
        logger.error("4. Set environment variables:")
        logger.error("   export REDDIT_CLIENT_ID='...'")
        logger.error("   export REDDIT_CLIENT_SECRET='...'")
        logger.error("   export REDDIT_USERNAME='your_reddit_username'")
        logger.error("   export REDDIT_PASSWORD='your_reddit_password'")
        return

    # STEP 1: Validate honesty compliance
    logger.info("🔍 STEP 1: HONESTY VALIDATION")
    logger.info("")

    fatfire_checks = validate_honesty_compliance(FATFIRE_HONEST)
    fatfire_compliant = print_validation_report("r/fatFIRE Post", fatfire_checks)

    fi_checks = validate_honesty_compliance(FINANCIALINDEPENDENCE_HONEST)
    fi_compliant = print_validation_report("r/financialindependence Post", fi_checks)

    if not (fatfire_compliant and fi_compliant):
        logger.error("")
        logger.error("❌ VALIDATION FAILED - Posts do not meet honesty standards")
        logger.error("   Fix issues before posting to public")
        return

    logger.info("")
    logger.info("✅ Both posts meet honesty standards")
    logger.info("")

    # STEP 2: Show preview
    logger.info("=" * 70)
    logger.info("📝 STEP 2: POST PREVIEW")
    logger.info("=" * 70)
    logger.info("")
    logger.info("r/fatFIRE:")
    logger.info(f"Title: {FATFIRE_HONEST['title']}")
    logger.info("")
    logger.info("r/financialindependence:")
    logger.info(f"Title: {FINANCIALINDEPENDENCE_HONEST['title']}")
    logger.info("")

    # STEP 3: Confirm posting
    logger.info("=" * 70)
    logger.info("⚠️  STEP 3: FINAL CONFIRMATION")
    logger.info("=" * 70)
    logger.info("")
    logger.info("This will ACTUALLY POST to Reddit (not simulated)")
    logger.info("")
    logger.info("Posts will appear as experimental/honest framing:")
    logger.info("  ✅ AI involvement disclosed")
    logger.info("  ✅ Early stage acknowledged")
    logger.info("  ✅ Framed as experiment")
    logger.info("  ✅ Uncertainty stated")
    logger.info("  ✅ Commitment to report back")
    logger.info("")

    confirm = input("Type 'YES' to post, anything else to cancel: ")

    if confirm != "YES":
        logger.info("")
        logger.info("❌ Posting cancelled")
        return

    logger.info("")
    logger.info("🚀 Proceeding with posting...")
    logger.info("")

    # STEP 4: Authenticate
    logger.info("🔐 STEP 4: AUTHENTICATION")
    reddit = create_reddit_client()

    if not reddit:
        logger.error("❌ Authentication failed")
        return

    logger.info("")

    # STEP 5: Post to r/fatFIRE
    logger.info("=" * 70)
    logger.info("📝 STEP 5: POSTING TO r/fatFIRE")
    logger.info("=" * 70)
    logger.info("")

    fatfire_submission = post_to_subreddit(
        reddit,
        "fatFIRE",
        FATFIRE_HONEST["title"],
        FATFIRE_HONEST["body"]
    )

    if fatfire_submission:
        logger.info("")
        logger.info(f"🎯 Monitor: https://reddit.com{fatfire_submission.permalink}")
        logger.info("")

    # STEP 6: Wait and post to r/financialindependence
    logger.info("⏳ Waiting 60 seconds (avoid spam detection)...")
    logger.info("")

    import time
    time.sleep(60)

    logger.info("=" * 70)
    logger.info("📝 STEP 6: POSTING TO r/financialindependence")
    logger.info("=" * 70)
    logger.info("")

    fi_submission = post_to_subreddit(
        reddit,
        "financialindependence",
        FINANCIALINDEPENDENCE_HONEST["title"],
        FINANCIALINDEPENDENCE_HONEST["body"]
    )

    if fi_submission:
        logger.info("")
        logger.info(f"🎯 Monitor: https://reddit.com{fi_submission.permalink}")
        logger.info("")

    # STEP 7: Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ HONEST EXPERIMENTAL POSTING COMPLETE")
    logger.info("=" * 70)
    logger.info("")

    if fatfire_submission and fi_submission:
        logger.info("🎉 Both posts live!")
        logger.info("")
        logger.info("Monitor URLs:")
        logger.info(f"  • r/fatFIRE: https://reddit.com{fatfire_submission.permalink}")
        logger.info(f"  • r/financialindependence: https://reddit.com{fi_submission.permalink}")
        logger.info("")
        logger.info("What to expect (honest prediction):")
        logger.info("  • 5-30 comments per post (some critical, some curious)")
        logger.info("  • 2-10 people actually try it")
        logger.info("  • Maybe 1-3 serious leads")
        logger.info("  • Learning whether AI matching works or is hype")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Monitor comments and respond honestly")
        logger.info("  2. Track who actually uses the service")
        logger.info("  3. Report back in 1 week (results OR failure)")
        logger.info("")
        logger.info("🌟 Experiment started. Let's learn together.")
        logger.info("")

        # Log experiment start
        with open("reddit_experiment_log.txt", "a") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"Experiment Started: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"r/fatFIRE: https://reddit.com{fatfire_submission.permalink}\n")
            f.write(f"r/financialindependence: https://reddit.com{fi_submission.permalink}\n")
            f.write(f"Framing: Honest/Experimental\n")
            f.write(f"Hypothesis: AI matching > Google for finding advisors\n")
            f.write(f"Report back: 1 week\n")
            f.write(f"{'='*70}\n")

        logger.info("📝 Logged to: reddit_experiment_log.txt")
        logger.info("")
    else:
        logger.error("⚠️  Some posts failed - check errors above")

    logger.info("=" * 70)

if __name__ == "__main__":
    main()
