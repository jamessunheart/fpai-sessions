#!/usr/bin/env python3
"""
🎯 REDDIT AUTOMATION MODULE
Full automation via PRAW (Python Reddit API Wrapper)

Session #6 (Catalyst) - Outreach Integration
Cost: $0 (Free with Reddit account)
Automation: 100%
"""

import os
import praw
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class RedditPost:
    """Reddit post data"""
    subreddit: str
    title: str
    body: str
    url: Optional[str] = None
    post_id: Optional[str] = None
    score: int = 0
    num_comments: int = 0
    created_at: Optional[str] = None
    status: str = "pending"  # pending, posted, failed


@dataclass
class RedditLead:
    """Lead extracted from Reddit"""
    username: str
    comment_text: str
    post_id: str
    subreddit: str
    email: Optional[str] = None
    needs: str = ""
    source: str = "reddit"
    created_at: str = ""


class RedditModule:
    """
    Automates Reddit posting and lead monitoring
    100% automated customer acquisition
    """

    def __init__(self, config_file: str = None):
        """
        Initialize Reddit automation

        Setup instructions:
        1. Create Reddit account
        2. Go to: https://www.reddit.com/prefs/apps
        3. Click "Create App" or "Create Another App"
        4. Select "script"
        5. Get client_id and client_secret
        6. Save to config file or environment variables
        """
        self.config = self.load_config(config_file)
        self.reddit = self.authenticate()
        self.state_file = "/Users/jamessunheart/Development/SERVICES/phase1-execution-engine/data/reddit_state.json"
        self.load_state()

    def load_config(self, config_file: Optional[str]) -> Dict:
        """Load Reddit API credentials"""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)

        # Try environment variables
        return {
            "client_id": os.environ.get("REDDIT_CLIENT_ID"),
            "client_secret": os.environ.get("REDDIT_CLIENT_SECRET"),
            "username": os.environ.get("REDDIT_USERNAME"),
            "password": os.environ.get("REDDIT_PASSWORD"),
            "user_agent": "I_MATCH_Bot/1.0 by /u/your_username"
        }

    def authenticate(self) -> praw.Reddit:
        """Authenticate with Reddit API"""
        try:
            reddit = praw.Reddit(
                client_id=self.config["client_id"],
                client_secret=self.config["client_secret"],
                user_agent=self.config["user_agent"],
                username=self.config["username"],
                password=self.config["password"]
            )

            # Test authentication
            reddit.user.me()
            print(f"✅ Authenticated as: u/{reddit.user.me().name}")

            return reddit

        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print("\n📋 Setup instructions:")
            print("1. Go to: https://www.reddit.com/prefs/apps")
            print("2. Create app (select 'script')")
            print("3. Set environment variables:")
            print("   export REDDIT_CLIENT_ID='...'")
            print("   export REDDIT_CLIENT_SECRET='...'")
            print("   export REDDIT_USERNAME='...'")
            print("   export REDDIT_PASSWORD='...'")
            raise

    def load_state(self):
        """Load module state"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                "posts": [],
                "leads": [],
                "total_posts": 0,
                "total_leads": 0,
                "last_updated": None
            }

    def save_state(self):
        """Save module state"""
        self.state["last_updated"] = datetime.utcnow().isoformat()
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def post(self, subreddit_name: str, title: str, body: str) -> RedditPost:
        """
        Post to subreddit (100% automated)

        Args:
            subreddit_name: e.g., "fatFIRE"
            title: Post title
            body: Post body (selftext)

        Returns:
            RedditPost with post_id and url
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            # Submit post
            submission = subreddit.submit(title=title, selftext=body)

            post = RedditPost(
                subreddit=subreddit_name,
                title=title,
                body=body,
                url=f"https://reddit.com{submission.permalink}",
                post_id=submission.id,
                score=submission.score,
                num_comments=submission.num_comments,
                created_at=datetime.utcnow().isoformat(),
                status="posted"
            )

            print(f"✅ Posted to r/{subreddit_name}")
            print(f"   URL: {post.url}")

            # Save to state
            self.state["posts"].append(asdict(post))
            self.state["total_posts"] += 1
            self.save_state()

            return post

        except Exception as e:
            print(f"❌ Post failed: {e}")

            post = RedditPost(
                subreddit=subreddit_name,
                title=title,
                body=body,
                status="failed"
            )

            self.state["posts"].append(asdict(post))
            self.save_state()

            return post

    def monitor_comments(self, post_id: str, keywords: List[str] = None) -> List[RedditLead]:
        """
        Monitor post comments for leads

        Args:
            post_id: Reddit post ID
            keywords: Optional keywords to filter (e.g., ["interested", "want", "need"])

        Returns:
            List of RedditLead objects
        """
        if keywords is None:
            keywords = ["interested", "want", "need", "looking for", "dm", "link"]

        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)  # Get all comments

            leads = []

            for comment in submission.comments.list():
                comment_text = comment.body.lower()

                # Check if comment matches keywords
                if any(keyword in comment_text for keyword in keywords):
                    lead = RedditLead(
                        username=comment.author.name if comment.author else "[deleted]",
                        comment_text=comment.body,
                        post_id=post_id,
                        subreddit=submission.subreddit.display_name,
                        needs="financial advisor",  # Infer from context
                        source="reddit",
                        created_at=datetime.utcnow().isoformat()
                    )

                    leads.append(lead)
                    print(f"  ✅ Lead found: u/{lead.username}")

            # Save to state
            for lead in leads:
                self.state["leads"].append(asdict(lead))
                self.state["total_leads"] += 1

            self.save_state()

            return leads

        except Exception as e:
            print(f"❌ Monitoring failed: {e}")
            return []

    def monitor_all_posts(self, keywords: List[str] = None) -> List[RedditLead]:
        """
        Monitor all posted submissions for leads

        Returns:
            Combined list of all leads
        """
        all_leads = []

        for post_data in self.state["posts"]:
            if post_data["status"] == "posted" and post_data["post_id"]:
                print(f"\n📊 Monitoring r/{post_data['subreddit']} post...")
                leads = self.monitor_comments(post_data["post_id"], keywords)
                all_leads.extend(leads)

        print(f"\n✅ Total leads found: {len(all_leads)}")
        return all_leads

    def get_post_stats(self, post_id: str) -> Dict:
        """Get statistics for a post"""
        try:
            submission = self.reddit.submission(id=post_id)

            return {
                "score": submission.score,
                "upvote_ratio": submission.upvote_ratio,
                "num_comments": submission.num_comments,
                "url": f"https://reddit.com{submission.permalink}"
            }

        except Exception as e:
            print(f"❌ Stats fetch failed: {e}")
            return {}

    def test_connection(self) -> bool:
        """Test if Reddit API is working"""
        try:
            user = self.reddit.user.me()
            karma = user.link_karma + user.comment_karma
            print(f"✅ Connected as u/{user.name} (karma: {karma})")
            return True
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False


def main():
    """Demo Reddit automation"""

    print("\n🎯 REDDIT AUTOMATION MODULE - Demo\n")

    # Initialize
    try:
        reddit = RedditModule()
    except Exception as e:
        print(f"\n❌ Setup required. Follow instructions above.")
        return

    # Test connection
    if not reddit.test_connection():
        return

    print("\n" + "="*60)
    print("REDDIT AUTOMATION CAPABILITIES")
    print("="*60)

    # Demo posts (using test content)
    demo_posts = [
        {
            "subreddit": "test",  # Safe for testing
            "title": "I MATCH - AI Financial Advisor Matching (Test Post)",
            "body": """This is a test post for the I MATCH automation system.

In production, this would post to r/fatFIRE with:
- Compelling story
- Clear value proposition
- Call to action
- Link to service

Example: http://198.54.123.234:8401/

(This is just a test - please ignore)"""
        }
    ]

    print("\n📝 Example Post Content:")
    print(f"   Title: {demo_posts[0]['title'][:50]}...")
    print(f"   Subreddit: r/{demo_posts[0]['subreddit']}")

    print("\n⚠️  To actually post, uncomment the code below:")
    print("   # post = reddit.post(**demo_posts[0])")

    # Uncomment to actually post (will post to r/test for safety)
    # post = reddit.post(**demo_posts[0])

    print("\n✅ Reddit module ready!")
    print("   - 100% automated posting")
    print("   - Automatic lead monitoring")
    print("   - $0 cost (free API)")

    print("\n📊 Current State:")
    print(f"   Total posts: {reddit.state['total_posts']}")
    print(f"   Total leads: {reddit.state['total_leads']}")


if __name__ == "__main__":
    main()
