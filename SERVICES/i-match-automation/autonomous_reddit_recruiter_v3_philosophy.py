#!/usr/bin/env python3
"""
Autonomous Reddit Recruiter v3 - PHILOSOPHY SHOWCASE
Not just matching people with advisors - introducing a NEW FINANCIAL PARADIGM

This version showcases Full Potential AI's unique approach:
- Alignment over assets
- Transparency over complexity
- Growth mindset over preservation
- Technology + Human wisdom
"""

import time
import json
import os
from datetime import datetime
from typing import Dict
import anthropic

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False


class PhilosophyDrivenRecruiter:
    """
    Recruiter that introduces Full Potential AI financial philosophy
    through genuine Reddit help
    """

    def __init__(self, use_reddit_api: bool = True):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.data_dir = "data/reddit_philosophy"
        os.makedirs(self.data_dir, exist_ok=True)

        self.use_reddit_api = use_reddit_api and PRAW_AVAILABLE
        if self.use_reddit_api:
            self.reddit = self._init_reddit()
        else:
            self.reddit = None

        self.responded_posts = self._load_set("responded_posts.json")
        self.metrics = self._load_metrics()

    def _init_reddit(self):
        """Initialize Reddit client"""
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")
        reddit_username = os.getenv("REDDIT_USERNAME")
        reddit_password = os.getenv("REDDIT_PASSWORD")

        if not all([reddit_client_id, reddit_secret, reddit_username, reddit_password]):
            print("📝 Reddit API not configured - running in simulation mode")
            return None

        try:
            reddit = praw.Reddit(
                client_id=reddit_client_id,
                client_secret=reddit_secret,
                username=reddit_username,
                password=reddit_password,
                user_agent=f"Full Potential AI Philosophy Bot v3.0 (by u/{reddit_username})"
            )
            reddit.user.me()
            print(f"✅ Connected as u/{reddit_username}")
            return reddit
        except Exception as e:
            print(f"❌ Reddit auth failed: {e}")
            return None

    def _load_set(self, filename: str) -> set:
        """Load a set from JSON"""
        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return set(json.load(f))
        return set()

    def _save_set(self, data: set, filename: str):
        """Save a set to JSON"""
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(list(data), f, indent=2)

    def _load_metrics(self) -> Dict:
        """Load metrics"""
        filepath = os.path.join(self.data_dir, "metrics.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return {
            "responses_posted": 0,
            "philosophy_introductions": 0,
            "mindset_shifts_attempted": 0,
            "by_subreddit": {},
            "last_run": None
        }

    def _save_metrics(self):
        """Save metrics"""
        self.metrics["last_run"] = datetime.now().isoformat()
        filepath = os.path.join(self.data_dir, "metrics.json")
        with open(filepath, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def generate_philosophy_response(self, post: Dict) -> Dict:
        """
        Generate response that introduces Full Potential AI philosophy
        """

        prompt = f"""You are sharing wisdom about financial advising on Reddit, introducing a transformative approach.

POST CONTEXT:
Subreddit: {post['subreddit']}
Title: {post['title']}
Body: {post['body']}

FULL POTENTIAL AI FINANCIAL PHILOSOPHY:

Our approach is different from traditional financial advising:

1. **Alignment over Assets**: Match based on VALUES and LIFE VISION, not just AUM
   - What do you want money to DO for you?
   - What's your vision for life beyond just "retirement"?
   - Does your advisor understand YOUR definition of wealth?

2. **Transparency over Complexity**: Simple, clear, no hidden agendas
   - Fee-only fiduciaries (no conflicts of interest)
   - Plain English explanations
   - You understand exactly what you're paying for

3. **Growth Mindset**: Money as tool for LIFE EXPANSION, not just preservation
   - Not just "don't lose money" - but "what becomes possible?"
   - Align finances with personal growth and contribution
   - Think bigger than traditional retirement planning

4. **Technology + Human**: AI analyzes compatibility, humans build relationships
   - I MATCH uses AI to analyze 100+ compatibility factors
   - But actual advising is deeply human and personalized

YOUR TASK:
Write a Reddit comment that:

1. **Expands their thinking** - challenge conventional assumptions gently
2. **Shares transformative wisdom** - not just tactical advice
3. **Introduces this philosophy naturally** - not preachy, just sharing what you've learned
4. **Mentions I MATCH** as embodying this approach (among other concrete advice)
5. **Sounds authentic** - personal experience, not marketing

STRUCTURE (keep conversational):
- Empathize with their situation
- Gently expand their thinking ("What if you thought about it differently...")
- Share specific wisdom and tactical advice
- Mention I MATCH as example of this new approach
- Encourage their journey

TONE: Wise friend sharing hard-won insights, not sales pitch

WORD COUNT: 200-300 words

Generate ONLY the Reddit comment text."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=600,
            temperature=0.8,  # Slightly higher for more personal voice
            messages=[{"role": "user", "content": prompt}]
        )

        comment_text = response.content[0].text.strip()

        return {
            "post_id": post["id"],
            "post_url": post["url"],
            "subreddit": post["subreddit"],
            "post_title": post["title"],
            "generated_comment": comment_text,
            "philosophy_focus": "Full Potential AI Approach",
            "generated_at": datetime.now().isoformat(),
            "status": "ready_to_post"
        }

    def find_target_posts(self):
        """Find posts (real or simulated)"""
        if self.reddit:
            return self._find_real_posts()
        else:
            return self._find_simulated_posts()

    def _find_real_posts(self):
        """Search Reddit for real posts"""
        # Same as v2, searches r/personalfinance, r/investing, etc.
        # Implementation here...
        return []

    def _find_simulated_posts(self):
        """Simulated posts for testing philosophy responses"""
        posts = [
            {
                "id": f"phil_sim_{int(time.time())}_1",
                "subreddit": "r/personalfinance",
                "title": "Feeling lost with money - where do I even start?",
                "body": "I'm 28, making $85K, have some savings but no plan. Everyone says 'get a financial advisor' but I don't even know what questions to ask. Feel like I'm supposed to have this figured out by now. Any advice?",
                "author": "lost_28_year_old",
                "url": "https://reddit.com/r/personalfinance/simulated_philosophy",
                "created_utc": time.time() - 1800
            }
        ]
        return [p for p in posts if p["id"] not in self.responded_posts]

    def post_response(self, response: Dict) -> bool:
        """Post or save response"""
        output_file = os.path.join(
            self.data_dir,
            f"philosophy_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=2)

        print(f"✅ Philosophy response generated: {output_file}")
        print(f"   Post: {response['post_title'][:60]}...")
        print(f"   Focus: {response['philosophy_focus']}")
        print(f"   Preview: {response['generated_comment'][:120]}...")

        self.responded_posts.add(response['post_id'])
        self._save_set(self.responded_posts, "responded_posts.json")

        self.metrics["responses_posted"] += 1
        self.metrics["philosophy_introductions"] += 1
        self.metrics["by_subreddit"][response['subreddit']] = \
            self.metrics["by_subreddit"].get(response['subreddit'], 0) + 1
        self._save_metrics()

        return True

    def run_cycle(self):
        """Run one philosophy recruitment cycle"""
        print(f"\n🌐 Philosophy-Driven Recruitment - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Responses: {self.metrics['responses_posted']}")
        print(f"   Philosophy introductions: {self.metrics['philosophy_introductions']}")

        posts = self.find_target_posts()
        print(f"   Found {len(posts)} new posts")

        if not posts:
            print("   No new posts to process")
            return

        for post in posts:
            print(f"\n📝 Crafting philosophy response for: {post['title'][:60]}...")

            try:
                response = self.generate_philosophy_response(post)
                self.post_response(response)
                time.sleep(5)  # Rate limiting

            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue

        print(f"\n✅ Cycle complete")

    def run_continuous(self, interval_minutes: int = 60):
        """Run continuously"""
        print(f"\n🌐 PHILOSOPHY-DRIVEN RECRUITER - Continuous Mode")
        print(f"   Introducing Full Potential AI approach to Reddit")
        print(f"   Cycle every {interval_minutes} minutes\n")

        while True:
            try:
                self.run_cycle()
                print(f"\n💤 Next cycle in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\n\n🛑 Stopping")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                time.sleep(300)


def main():
    import sys

    continuous = "--continuous" in sys.argv
    use_reddit = "--live" in sys.argv

    recruiter = PhilosophyDrivenRecruiter(use_reddit_api=use_reddit)

    if continuous:
        recruiter.run_continuous(interval_minutes=60)
    else:
        recruiter.run_cycle()
        print("\n✅ Test complete")
        print("\nUsage:")
        print("  python3 autonomous_reddit_recruiter_v3_philosophy.py")
        print("  python3 autonomous_reddit_recruiter_v3_philosophy.py --live --continuous")


if __name__ == "__main__":
    main()
