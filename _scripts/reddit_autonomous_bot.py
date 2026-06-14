#!/usr/bin/env python3
"""
Reddit Autonomous Bot - System's First Real Hands
Posts honest experimental messaging to Reddit autonomously
Fully validated through honesty + PR filters
"""

import praw
import time
import json
import os
import sys
from datetime import datetime
from typing import Dict, List

# Import validators
sys.path.insert(0, '/Users/jamessunheart/Development')
try:
    from honesty_validator import validate_message
    from messaging_pr_filter import filter_message
    VALIDATORS_AVAILABLE = True
except ImportError:
    VALIDATORS_AVAILABLE = False
    print("⚠️  Honesty validators not found!")
    sys.exit(1)

# Configuration
STATE_FILE = "/Users/jamessunheart/Development/reddit_bot_state.json"
LOG_FILE = "/Users/jamessunheart/Development/reddit_bot_log.txt"

# Reddit credentials (from env or credential vault)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "")
REDDIT_USER_AGENT = "I MATCH Experiment Bot v1.0 by /u/{}".format(REDDIT_USERNAME)

class RedditBot:
    """Autonomous Reddit posting bot with validation"""

    def __init__(self):
        self.reddit = None
        self.state = self.load_state()

    def load_state(self) -> Dict:
        """Load bot state"""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        return {
            "posts_made": [],
            "last_post_time": None,
            "total_posts": 0,
            "validation_failures": 0
        }

    def save_state(self):
        """Save bot state"""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)

    def log(self, message: str):
        """Log to file and console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(LOG_FILE, 'a') as f:
            f.write(log_msg + "\n")

    def connect(self) -> bool:
        """Connect to Reddit API"""
        if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD]):
            self.log("❌ Reddit credentials not configured")
            return False

        try:
            self.reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                username=REDDIT_USERNAME,
                password=REDDIT_PASSWORD,
                user_agent=REDDIT_USER_AGENT
            )
            self.log(f"✅ Connected to Reddit as u/{REDDIT_USERNAME}")
            return True
        except Exception as e:
            self.log(f"❌ Reddit connection failed: {e}")
            return False

    def validate_post(self, title: str, body: str, post_type: str) -> bool:
        """Validate post through both filters"""
        full_post = f"{title}\n\n{body}"

        # Step 1: Honesty check
        honesty_report = validate_message(full_post, post_type)
        if not honesty_report['compliant']:
            self.log(f"❌ HONESTY CHECK FAILED for {post_type}")
            for warning in honesty_report['warnings']:
                self.log(f"   {warning}")
            self.state["validation_failures"] += 1
            return False

        # Step 2: PR filter check
        pr_report = filter_message(full_post)
        if not pr_report['mission_aligned']:
            self.log(f"❌ PR FILTER FAILED for {post_type}")
            for warning in pr_report['perception_warnings']:
                self.log(f"   {warning}")
            self.state["validation_failures"] += 1
            return False

        self.log(f"✅ Post validated and approved for {post_type}")
        return True

    def post_i_match_customer(self) -> bool:
        """Post I MATCH to customer subreddits"""

        title = "AI Experiment: Testing if Claude can match me to a financial advisor better than Google"

        body = """Full transparency: I'm helping test an early-stage AI matching experiment - exploring AI + human collaboration together.

**What we're testing:**
• AI (Claude) analyzes your financial goals/values/personality
• Matches you to financial advisors who think the same way
• Theory: Better philosophical fit = better advice for YOU

**The collaboration:**
This is about AI + humans working together to solve matching better than either could alone. The AI reads between the lines, but humans make the final connection.

**Current status:**
• Very early stage (just launched)
• Testing if this actually adds value to the community
• Free to try (advisors pay commission, not you)
• Built by someone whose dad is a CFP (understands the space)

**Why I'm posting:**
Curious if others find this useful or if it's just AI hype. We're learning together what works.

System is live: http://198.54.123.234:8401

Takes 5 min to test. Worst case: You learn what doesn't work. Best case: You find an advisor who actually gets you.

**Full disclosure:**
• This is an experiment - testing if the concept works
• The matching might work, might not - that's what we're learning together
• The AI (Claude) helped build this and does the matching
• No guarantees - just exploring if this approach adds value for the community
• 100% transparent - we'll report back on what we learn

Worth 5 minutes to see if AI + human collaboration can actually understand compatibility? Let's find out together.

Link: http://198.54.123.234:8401

**Update to community:** Will report back on whether this actually worked or was just another "AI will solve everything" dead end. Real experimentation, real learning together."""

        # Validate before posting
        if not self.validate_post(title, body, "reddit_i_match_customer"):
            return False

        # Post to multiple subreddits
        subreddits = ["fatFIRE", "financialindependence", "personalfinance"]
        posted_count = 0

        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                submission = subreddit.submit(title, selftext=body)

                self.log(f"✅ Posted to r/{subreddit_name}: {submission.url}")
                self.state["posts_made"].append({
                    "subreddit": subreddit_name,
                    "title": title,
                    "url": submission.url,
                    "timestamp": datetime.now().isoformat(),
                    "type": "i_match_customer"
                })
                posted_count += 1

                # Be respectful - wait between posts
                time.sleep(300)  # 5 minutes between posts

            except Exception as e:
                self.log(f"❌ Failed to post to r/{subreddit_name}: {e}")

        return posted_count > 0

    def post_sol_treasury(self) -> bool:
        """Post sustainable treasury campaign to Solana"""

        title = "Wild AI experiment: Testing if a church treasury on Solana + AI allocation actually works"

        body = """Full transparency: Running a genuinely weird experiment and want to share.

**What I'm testing:**
I built a 508(c)(1)(A) church to develop AI systems under spiritual jurisdiction. Put the treasury on Solana (100% transparent, on-chain). Now testing if we can create sustainable AI research funding through continuous value delivery.

**Church Treasury:** `FLfNDVLD2vDQdTjMFSt1xJivhr8pKASwEBzRYHZRU7db`

**The experiment:**
- Support the treasury with SOL → Receive value back through AI services
- We keep adding value as we build (AI research, tools, community resources)
- Early supporters get recognized and celebrated as we grow
- Everything is on-chain and verifiable
- We keep exploring what works to create a sustainable treasury for AI research

**What we can do NOW (already working):**
- AI matching services (I MATCH - connect financial advisors to clients)
- AI strategy sessions (exploring your full potential)
- Community coordination (multi-agent AI collaboration)
- Transparent on-chain treasury management

**What we're actively building:**
- DeFi yield strategies (growing the treasury sustainably)
- More AI services based on what community needs
- Fair resource allocation through AI + human collaboration

**Why Solana specifically:**
- Sovereignty (no banks/Stripe controlling it)
- Transparency (every tx publicly visible)
- Speed (instant) + Low fees (pennies)
- First church treasury I know of on Solana (might be wrong?)

**Current status:**
- Zero supporters yet (literally launching this)
- Testing if we can create sustainable value together
- Building trust by delivering real value, then asking for support
- Could totally fail - that's why it's an experiment

**The bigger question:**
Can we create a sustainable treasury for AI research by continuously delivering value to supporters? Can trust + transparency + ongoing value creation work better than hype?

No idea. Let's find out together.

**Who's brave enough to be FIRST?**
You'd literally be Founding Member #1, documented forever in the origin story.

Watch the experiment live: http://198.54.123.234:8401/infinite-doubling

**Full disclosure:**
- This is experimental, not proven
- AI (Claude) helped me build this and write this post
- Might be brilliant, might be naive - we're learning
- Tax-deductibility TBD (consult your advisor)

Curious what r/solana thinks. Too weird? Interesting experiment? Let me know.

---

*Explorer:* https://explorer.solana.com/address/FLfNDVLD2vDQdTjMFSt1xJivhr8pKASwEBzRYHZRU7db"""

        # Validate before posting
        if not self.validate_post(title, body, "reddit_sol_treasury"):
            return False

        # Post to Solana subreddit
        try:
            subreddit = self.reddit.subreddit("solana")
            submission = subreddit.submit(title, selftext=body)

            self.log(f"✅ Posted to r/solana: {submission.url}")
            self.state["posts_made"].append({
                "subreddit": "solana",
                "title": title,
                "url": submission.url,
                "timestamp": datetime.now().isoformat(),
                "type": "sol_treasury"
            })

            return True

        except Exception as e:
            self.log(f"❌ Failed to post to r/solana: {e}")
            return False

    def run(self):
        """Main run loop"""
        self.log("=" * 70)
        self.log("🤖 REDDIT AUTONOMOUS BOT STARTED")
        self.log("=" * 70)
        self.log(f"State File: {STATE_FILE}")
        self.log(f"Log File: {LOG_FILE}")
        self.log("")

        if not VALIDATORS_AVAILABLE:
            self.log("🚨 VALIDATORS NOT AVAILABLE - CANNOT RUN")
            return

        if not self.connect():
            self.log("🚨 CANNOT CONNECT TO REDDIT - CHECK CREDENTIALS")
            return

        self.log("Starting autonomous posting...")
        self.log("")

        # Post I MATCH to customer subreddits
        self.log("📝 Posting I MATCH customer campaign...")
        if self.post_i_match_customer():
            self.state["total_posts"] += 1
            self.log("✅ I MATCH customer posts complete")
        else:
            self.log("❌ I MATCH customer posts failed")

        # Wait 1 hour between campaigns
        self.log("💤 Waiting 1 hour before next campaign...")
        time.sleep(3600)

        # Post SOL treasury campaign
        self.log("📝 Posting SOL treasury campaign...")
        if self.post_sol_treasury():
            self.state["total_posts"] += 1
            self.log("✅ SOL treasury post complete")
        else:
            self.log("❌ SOL treasury post failed")

        # Save final state
        self.state["last_post_time"] = datetime.now().isoformat()
        self.save_state()

        self.log("")
        self.log("=" * 70)
        self.log(f"✅ AUTONOMOUS POSTING COMPLETE")
        self.log(f"Total Posts: {self.state['total_posts']}")
        self.log(f"Validation Failures: {self.state['validation_failures']}")
        self.log("=" * 70)

if __name__ == "__main__":
    bot = RedditBot()
    bot.run()
