#!/usr/bin/env python3
"""
Autonomous Reddit Recruiter v2 - FULL AUTOMATION
Continuously finds people looking for services and introduces them to I MATCH

PHASE 2: Real Reddit API integration with PRAW
"""

import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
import anthropic

# Reddit API
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    print("⚠️  PRAW not installed. Install with: pip install praw")


class AutonomousRedditRecruiterV2:
    """
    Fully autonomous Reddit recruiter with real API integration
    """

    def __init__(self, use_reddit_api: bool = True):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.data_dir = "data/reddit_outreach"
        os.makedirs(self.data_dir, exist_ok=True)

        # Reddit API setup
        self.use_reddit_api = use_reddit_api and PRAW_AVAILABLE
        if self.use_reddit_api:
            self.reddit = self._init_reddit()
        else:
            self.reddit = None
            print("📝 Running in simulation mode (Reddit API not configured)")

        # Track what we've already responded to
        self.responded_file = f"{self.data_dir}/responded_posts.json"
        self.responded_posts = self._load_responded_posts()

        # Track performance
        self.metrics_file = f"{self.data_dir}/recruitment_metrics.json"
        self.metrics = self._load_metrics()

    def _init_reddit(self):
        """Initialize Reddit API client"""
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")
        reddit_username = os.getenv("REDDIT_USERNAME")
        reddit_password = os.getenv("REDDIT_PASSWORD")

        if not all([reddit_client_id, reddit_secret, reddit_username, reddit_password]):
            print("⚠️  Reddit credentials not found. Running in simulation mode.")
            print("   Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD")
            return None

        try:
            reddit = praw.Reddit(
                client_id=reddit_client_id,
                client_secret=reddit_secret,
                username=reddit_username,
                password=reddit_password,
                user_agent="I MATCH Recruiter v2.0 (by u/{})".format(reddit_username)
            )
            # Test authentication
            reddit.user.me()
            print(f"✅ Connected to Reddit as u/{reddit_username}")
            return reddit
        except Exception as e:
            print(f"❌ Reddit authentication failed: {str(e)}")
            return None

    def _load_responded_posts(self) -> set:
        """Load list of posts we've already responded to"""
        if os.path.exists(self.responded_file):
            with open(self.responded_file, 'r') as f:
                return set(json.load(f))
        return set()

    def _save_responded_posts(self):
        """Save updated list of responded posts"""
        with open(self.responded_file, 'w') as f:
            json.dump(list(self.responded_posts), f, indent=2)

    def _load_metrics(self) -> Dict:
        """Load recruitment metrics"""
        if os.path.exists(self.metrics_file):
            with open(self.metrics_file, 'r') as f:
                return json.load(f)
        return {
            "responses_posted": 0,
            "sign_ups_generated": 0,
            "last_run": None,
            "by_subreddit": {},
            "by_template": {},
            "reddit_karma": 0,
            "successful_posts": 0,
            "failed_posts": 0
        }

    def _save_metrics(self):
        """Save updated metrics"""
        self.metrics["last_run"] = datetime.now().isoformat()
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def find_target_posts_real(self) -> List[Dict]:
        """
        Find REAL Reddit posts using Reddit API
        """
        if not self.reddit:
            return []

        target_posts = []

        # Search queries for each community
        searches = [
            {"subreddit": "personalfinance", "query": "financial advisor", "limit": 5},
            {"subreddit": "investing", "query": "how to find advisor", "limit": 3},
            {"subreddit": "entrepreneur", "query": "executive coach", "limit": 3},
            {"subreddit": "startups", "query": "looking for coach OR need coach", "limit": 2},
            {"subreddit": "Christianity", "query": "starting church OR ministry legal", "limit": 2},
        ]

        for search in searches:
            try:
                subreddit = self.reddit.subreddit(search["subreddit"])

                # Search recent posts (last 24 hours)
                for post in subreddit.search(
                    search["query"],
                    time_filter="day",
                    limit=search["limit"]
                ):
                    # Skip if already responded
                    if post.id in self.responded_posts:
                        continue

                    # Skip if it's our own post
                    if str(post.author) == self.reddit.user.me().name:
                        continue

                    # Skip if post is locked or archived
                    if post.locked or post.archived:
                        continue

                    # Skip if post has no body (link posts)
                    if not post.selftext or len(post.selftext) < 50:
                        continue

                    target_posts.append({
                        "id": post.id,
                        "subreddit": f"r/{post.subreddit.display_name}",
                        "title": post.title,
                        "body": post.selftext[:1000],  # Limit for API
                        "author": str(post.author),
                        "url": f"https://reddit.com{post.permalink}",
                        "created_utc": post.created_utc,
                        "score": post.score,
                        "num_comments": post.num_comments
                    })

            except Exception as e:
                print(f"   ⚠️  Error searching r/{search['subreddit']}: {str(e)}")
                continue

        return target_posts

    def find_target_posts_simulated(self) -> List[Dict]:
        """Simulated posts for testing"""
        simulated_posts = [
            {
                "id": f"sim_{int(time.time())}_1",
                "subreddit": "r/personalfinance",
                "title": "30F looking for financial advisor - how to choose?",
                "body": "Just got promoted with a big salary jump. Now dealing with RSUs, 401k decisions, and trying to buy a house. Feel overwhelmed. How do I find a good financial advisor who won't just try to sell me stuff?",
                "author": "tech_professional_30",
                "url": "https://reddit.com/r/personalfinance/simulated",
                "created_utc": time.time() - 1800
            }
        ]

        # Filter out already responded
        return [p for p in simulated_posts if p["id"] not in self.responded_posts]

    def find_target_posts(self) -> List[Dict]:
        """Find posts (real or simulated)"""
        if self.reddit:
            return self.find_target_posts_real()
        else:
            return self.find_target_posts_simulated()

    def analyze_post_and_generate_response(self, post: Dict) -> Dict:
        """Generate helpful response using Claude"""

        prompt = f"""You are helping someone on Reddit who is looking for professional services.

POST CONTEXT:
Subreddit: {post['subreddit']}
Title: {post['title']}
Body: {post['body']}

YOUR TASK:
Write a genuinely helpful Reddit comment that:
1. Shows you understand their specific situation
2. Provides actionable advice they can use immediately
3. Naturally mentions I MATCH as ONE helpful option (not the only option)
4. Sounds like a real person sharing their experience, not marketing

I MATCH INFO:
- AI-powered matching for financial advisors, executive coaches, and professionals
- Free for people seeking services (providers pay commission only if engaged)
- Analyzes compatibility: needs, values, communication style, specialization
- URL: http://198.54.123.234:8401/
- Currently in beta with limited spots

CRITICAL REQUIREMENTS:
- Be helpful FIRST - give real advice even without I MATCH
- Personal voice ("I was in the same boat...")
- Keep it 150-250 words max (Reddit attention span)
- Don't be salesy - sound like a friend helping
- Mention I MATCH as something that worked for YOU, alongside other resources

Generate ONLY the Reddit comment text."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )

        comment_text = response.content[0].text.strip()

        return {
            "post_id": post["id"],
            "post_url": post["url"],
            "subreddit": post["subreddit"],
            "post_title": post["title"],
            "generated_comment": comment_text,
            "generated_at": datetime.now().isoformat(),
            "status": "ready_to_post"
        }

    def post_comment_real(self, response: Dict) -> bool:
        """Post comment to Reddit using API"""
        if not self.reddit:
            return False

        try:
            # Get the submission
            submission = self.reddit.submission(id=response['post_id'])

            # Post comment
            comment = submission.reply(response['generated_comment'])

            print(f"✅ Posted to Reddit: {comment.permalink}")

            # Update metrics
            self.metrics["successful_posts"] += 1

            # Track karma (check after posting)
            time.sleep(2)
            comment.refresh()
            self.metrics["reddit_karma"] += comment.score

            return True

        except Exception as e:
            print(f"❌ Failed to post comment: {str(e)}")
            self.metrics["failed_posts"] += 1
            return False

    def post_comment_simulated(self, response: Dict) -> bool:
        """Save comment for manual posting"""
        output_file = f"{self.data_dir}/ready_to_post_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=2)

        print(f"📝 Response saved: {output_file}")
        print(f"   Post: {response['post_title'][:50]}...")
        print(f"   Preview: {response['generated_comment'][:100]}...")

        return True

    def post_comment(self, response: Dict) -> bool:
        """Post comment (real or simulated)"""
        # Post to Reddit
        if self.reddit:
            success = self.post_comment_real(response)
        else:
            success = self.post_comment_simulated(response)

        if success:
            # Mark as responded
            self.responded_posts.add(response['post_id'])
            self._save_responded_posts()

            # Update metrics
            self.metrics["responses_posted"] += 1
            subreddit = response['subreddit']
            self.metrics['by_subreddit'][subreddit] = self.metrics['by_subreddit'].get(subreddit, 0) + 1
            self._save_metrics()

        return success

    def run_recruitment_cycle(self):
        """Run one cycle of autonomous recruitment"""

        print(f"\n🔍 Recruitment Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Mode: {'🌐 LIVE (Reddit API)' if self.reddit else '📝 Simulation'}")
        print(f"   Total responses: {self.metrics['responses_posted']}")
        if self.reddit:
            print(f"   Reddit karma: {self.metrics['reddit_karma']}")

        # Find posts
        target_posts = self.find_target_posts()
        print(f"   Found {len(target_posts)} new posts to process")

        if not target_posts:
            print("   No new posts found")
            return

        # Process each post
        for post in target_posts:
            print(f"\n📝 Processing: {post['title'][:60]}...")
            print(f"   r/{post['subreddit'].replace('r/', '')} - {post.get('score', 0)}↑ - {post.get('num_comments', 0)} comments")

            try:
                # Generate response
                response = self.analyze_post_and_generate_response(post)

                # Post comment
                success = self.post_comment(response)

                if success:
                    # Rate limiting: wait between posts
                    wait_time = 90 if self.reddit else 5  # 90s for real posts, 5s for simulation
                    print(f"   ⏱️  Waiting {wait_time}s before next post...")
                    time.sleep(wait_time)

            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                continue

        print(f"\n✅ Cycle complete - {self.metrics['responses_posted']} total responses")

    def run_continuous(self, interval_minutes: int = 60):
        """Run continuously"""

        mode = "LIVE" if self.reddit else "SIMULATION"
        print(f"\n🤖 AUTONOMOUS REDDIT RECRUITER V2 - {mode} MODE")
        print(f"   Checking for posts every {interval_minutes} minutes")
        print(f"   Data: {self.data_dir}")
        print(f"   Press Ctrl+C to stop\n")

        cycle_count = 0

        while True:
            try:
                cycle_count += 1
                print(f"\n{'='*60}")
                print(f"CYCLE #{cycle_count}")
                print(f"{'='*60}")

                self.run_recruitment_cycle()

                print(f"\n💤 Next cycle in {interval_minutes} minutes...")
                print(f"   Time: {(datetime.now() + timedelta(minutes=interval_minutes)).strftime('%H:%M:%S')}")

                time.sleep(interval_minutes * 60)

            except KeyboardInterrupt:
                print("\n\n🛑 Stopping autonomous recruiter")
                print(f"   Final stats:")
                print(f"   - Total responses: {self.metrics['responses_posted']}")
                print(f"   - Successful: {self.metrics.get('successful_posts', 0)}")
                print(f"   - Failed: {self.metrics.get('failed_posts', 0)}")
                if self.reddit:
                    print(f"   - Reddit karma: {self.metrics['reddit_karma']}")
                break
            except Exception as e:
                print(f"\n❌ Error in cycle: {str(e)}")
                print(f"   Retrying in 5 minutes...")
                time.sleep(300)


def main():
    """Main entry point"""
    import sys

    # Check for continuous mode flag
    continuous = "--continuous" in sys.argv

    # Check for live mode flag (use real Reddit API)
    use_reddit = "--live" in sys.argv or os.getenv("USE_REDDIT_API") == "true"

    recruiter = AutonomousRedditRecruiterV2(use_reddit_api=use_reddit)

    if continuous:
        # Run continuously (default: every 60 minutes)
        recruiter.run_continuous(interval_minutes=60)
    else:
        # Run once (testing)
        recruiter.run_recruitment_cycle()
        print("\n✅ Test cycle complete")
        print("\nUsage:")
        print("  python3 autonomous_reddit_recruiter_v2.py               # Test (simulation)")
        print("  python3 autonomous_reddit_recruiter_v2.py --live        # Test (real Reddit)")
        print("  python3 autonomous_reddit_recruiter_v2.py --continuous  # Run forever (simulation)")
        print("  python3 autonomous_reddit_recruiter_v2.py --live --continuous  # FULL AUTO")


if __name__ == "__main__":
    main()
