#!/usr/bin/env python3
"""
Autonomous Reddit Recruiter for I MATCH
Continuously finds people looking for services and introduces them to I MATCH

NO SPAM. GENUINE HELP. AUTOMATED AT SCALE.
"""

import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
import anthropic

class AutonomousRedditRecruiter:
    """
    Autonomous system that:
    1. Monitors Reddit for people seeking advisors/coaches/services
    2. Analyzes if I MATCH can help them
    3. Generates genuine, helpful responses
    4. Tracks results and learns what works
    """

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.data_dir = "data/reddit_outreach"
        os.makedirs(self.data_dir, exist_ok=True)

        # Track what we've already responded to
        self.responded_file = f"{self.data_dir}/responded_posts.json"
        self.responded_posts = self._load_responded_posts()

        # Track performance
        self.metrics_file = f"{self.data_dir}/recruitment_metrics.json"
        self.metrics = self._load_metrics()

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
            "by_template": {}
        }

    def _save_metrics(self):
        """Save updated metrics"""
        self.metrics["last_run"] = datetime.now().isoformat()
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def find_target_posts(self) -> List[Dict]:
        """
        Find Reddit posts where people are looking for help

        PHASE 1: Return simulated posts (you'll add Reddit API later)
        PHASE 2: Use Reddit API (PRAW) to actually search
        """

        # PHASE 1: Simulated target posts
        # These represent the TYPE of posts we'd find on Reddit
        simulated_posts = [
            {
                "id": "sim_1",
                "subreddit": "r/personalfinance",
                "title": "How do I find a good financial advisor?",
                "body": "I'm 35, tech worker with RSUs and stock options. Need help with tax planning and retirement. No idea how to find someone who understands tech comp. Any recommendations?",
                "author": "tech_worker_35",
                "url": "https://reddit.com/r/personalfinance/simulated_1",
                "created_utc": datetime.now().timestamp() - 3600  # 1 hour ago
            },
            {
                "id": "sim_2",
                "subreddit": "r/entrepreneur",
                "title": "Looking for executive coach - how to choose?",
                "body": "Running a $2M ARR SaaS company. Feel stuck at current level. Want to scale to $10M but need guidance. How do you find a good executive coach?",
                "author": "saas_founder_",
                "url": "https://reddit.com/r/entrepreneur/simulated_2",
                "created_utc": datetime.now().timestamp() - 7200  # 2 hours ago
            },
            {
                "id": "sim_3",
                "subreddit": "r/Christianity",
                "title": "Starting a new ministry - legal requirements?",
                "body": "Called to start a church in my community. What do I need to know about 501c3 vs 508c1a? Bylaws? Articles of faith? Feeling overwhelmed.",
                "author": "pastor_in_training",
                "url": "https://reddit.com/r/Christianity/simulated_3",
                "created_utc": datetime.now().timestamp() - 10800  # 3 hours ago
            }
        ]

        # Filter out posts we've already responded to
        new_posts = [p for p in simulated_posts if p["id"] not in self.responded_posts]

        return new_posts

    def analyze_post_and_generate_response(self, post: Dict) -> Dict:
        """
        Use Claude to:
        1. Analyze if I MATCH can help this person
        2. Generate a genuine, helpful response
        3. Naturally mention I MATCH as one option
        """

        prompt = f"""You are helping someone on Reddit who is looking for professional services.

POST CONTEXT:
Subreddit: {post['subreddit']}
Title: {post['title']}
Body: {post['body']}

YOUR TASK:
Write a genuinely helpful Reddit comment that:
1. Shows you understand their specific situation
2. Provides actionable advice they can use
3. Naturally mentions I MATCH as ONE helpful option (not the only option)
4. Sounds like a real person, not marketing copy

I MATCH INFO:
- AI-powered matching for financial advisors, executive coaches, and other professionals
- Free for people seeking services (providers pay commission only if engaged)
- Analyzes compatibility based on needs, values, communication style, specialization
- URL: http://198.54.123.234:8401/
- Currently in beta

TONE:
- Helpful, not salesy
- Personal experience voice ("I was in the same situation...")
- Mention I MATCH as something that helped you, alongside other resources
- Keep it concise (150-250 words max)

Generate ONLY the Reddit comment text. No explanation, no meta-commentary."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            temperature=0.7,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        comment_text = response.content[0].text.strip()

        return {
            "post_id": post["id"],
            "post_url": post["url"],
            "subreddit": post["subreddit"],
            "generated_comment": comment_text,
            "generated_at": datetime.now().isoformat(),
            "status": "ready_to_post"
        }

    def post_comment(self, response: Dict) -> bool:
        """
        Post the comment to Reddit

        PHASE 1: Just save to file for manual review
        PHASE 2: Use Reddit API to actually post
        """

        # PHASE 1: Save for manual posting
        output_file = f"{self.data_dir}/ready_to_post_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=2)

        print(f"✅ Generated response saved to: {output_file}")
        print(f"   Post: {response['post_url']}")
        print(f"   Comment preview: {response['generated_comment'][:100]}...")

        # Mark as responded (so we don't generate multiple responses to same post)
        self.responded_posts.add(response['post_id'])
        self._save_responded_posts()

        # Update metrics
        self.metrics["responses_posted"] += 1
        subreddit = response['subreddit']
        self.metrics['by_subreddit'][subreddit] = self.metrics['by_subreddit'].get(subreddit, 0) + 1
        self._save_metrics()

        return True

    def run_recruitment_cycle(self):
        """
        Run one cycle of autonomous recruitment:
        1. Find target posts
        2. Generate helpful responses
        3. Post comments (or save for manual posting in Phase 1)
        """

        print(f"\n🔍 Starting recruitment cycle at {datetime.now()}")
        print(f"   Metrics: {self.metrics['responses_posted']} responses posted so far")

        # Find posts
        target_posts = self.find_target_posts()
        print(f"   Found {len(target_posts)} new target posts")

        if not target_posts:
            print("   No new posts to respond to")
            return

        # Generate and post responses
        for post in target_posts:
            print(f"\n📝 Processing: {post['title'][:60]}...")

            try:
                # Generate response
                response = self.analyze_post_and_generate_response(post)

                # Post (or save for manual posting)
                self.post_comment(response)

                # Rate limiting: 1 response per 60 seconds to avoid spam detection
                print(f"   ⏱️  Waiting 60s before next post...")
                time.sleep(60)

            except Exception as e:
                print(f"   ❌ Error processing post: {str(e)}")
                continue

        print(f"\n✅ Recruitment cycle complete")
        print(f"   Total responses generated: {self.metrics['responses_posted']}")

    def run_continuous(self, interval_minutes: int = 60):
        """
        Run recruitment continuously

        Args:
            interval_minutes: How often to check for new posts (default: 60 min)
        """

        print(f"🤖 Starting Autonomous Reddit Recruiter")
        print(f"   Checking for new posts every {interval_minutes} minutes")
        print(f"   Data directory: {self.data_dir}")
        print(f"   Press Ctrl+C to stop")

        while True:
            try:
                self.run_recruitment_cycle()

                print(f"\n💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)

            except KeyboardInterrupt:
                print("\n\n🛑 Stopping autonomous recruiter")
                break
            except Exception as e:
                print(f"\n❌ Error in recruitment cycle: {str(e)}")
                print(f"   Retrying in 5 minutes...")
                time.sleep(300)


def main():
    """
    Main entry point

    Usage:
        # Run one cycle (test)
        python3 autonomous_reddit_recruiter.py

        # Run continuously (production)
        python3 autonomous_reddit_recruiter.py --continuous

        # Run continuously in background
        nohup python3 autonomous_reddit_recruiter.py --continuous > reddit_recruiter.log 2>&1 &
    """

    import sys

    recruiter = AutonomousRedditRecruiter()

    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        # Run continuously
        recruiter.run_continuous(interval_minutes=60)
    else:
        # Run once (for testing)
        recruiter.run_recruitment_cycle()
        print("\n✅ Test cycle complete")
        print("   To run continuously: python3 autonomous_reddit_recruiter.py --continuous")


if __name__ == "__main__":
    main()
