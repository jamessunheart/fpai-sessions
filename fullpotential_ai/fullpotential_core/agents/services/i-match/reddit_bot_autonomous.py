#!/usr/bin/env python3
"""
Autonomous Reddit Bot - Posts without manual intervention
Uses Playwright to automate browser actions
"""
from playwright.sync_api import sync_playwright
import time
from pathlib import Path

def post_to_reddit(username, password, subreddit, title, content):
    """Post to Reddit using browser automation"""

    with sync_playwright() as p:
        # Launch browser (can be headless=True for background)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Login to Reddit
        print(f"Logging in as {username}...")
        page.goto("https://www.reddit.com/login")
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        time.sleep(3)

        # Navigate to subreddit
        print(f"Going to {subreddit}...")
        page.goto(f"https://www.reddit.com/{subreddit}/submit")
        time.sleep(2)

        # Create post
        print(f"Creating post: {title[:50]}...")
        page.click('button:has-text("Post")')  # Click "Post" tab
        page.fill('textarea[placeholder*="Title"]', title)
        page.fill('textarea[placeholder*="Text"]', content)

        # Submit
        print("Submitting post...")
        page.click('button:has-text("Post")')
        time.sleep(3)

        # Get post URL
        post_url = page.url
        print(f"✅ Posted: {post_url}")

        browser.close()
        return post_url

def auto_post_schedule():
    """Automatically post according to schedule"""

    # Load posts from reddit_posts_ready/
    posts_dir = Path("reddit_posts_ready")

    if not posts_dir.exists():
        print("❌ No posts found. Run autonomous_reddit_poster.py first.")
        return

    # Prompt for credentials
    username = input("Reddit username: ")
    password = input("Reddit password: ")

    print("\n🤖 Starting autonomous posting...")
    print("⚠️  Bot will post every other day at 9am EST")
    print("⚠️  Make sure to respond to comments manually!\n")

    # Load and post each file
    for post_file in sorted(posts_dir.glob("post_*.md")):
        with open(post_file) as f:
            content = f.read()

        # Extract title and content (simple parsing)
        lines = content.split('\n')
        title = None
        post_content = []
        in_content = False

        for line in lines:
            if "## TITLE" in line:
                title = lines[lines.index(line) + 2]  # Title is 2 lines after
            elif "## CONTENT" in line:
                in_content = True
            elif in_content and line.startswith("---"):
                break
            elif in_content:
                post_content.append(line)

        if title and post_content:
            subreddit = "r/FinancialPlanning"  # Extract from file if needed
            post_to_reddit(username, password, subreddit, title, '\n'.join(post_content))

            print(f"✅ Posted: {post_file.name}")
            print("⏳ Waiting 48 hours for next post...\n")
            time.sleep(48 * 60 * 60)  # Wait 2 days

if __name__ == "__main__":
    import sys
    if "--auto" in sys.argv:
        auto_post_schedule()
    else:
        print("Usage: python3 reddit_bot_autonomous.py --auto")
        print("This will start autonomous posting bot (requires credentials)")
