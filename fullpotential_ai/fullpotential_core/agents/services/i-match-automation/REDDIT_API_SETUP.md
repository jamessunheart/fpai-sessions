# Reddit API Setup for Autonomous Recruiter

## Current Status:

**Phase 1 (COMPLETE):**
✅ Autonomous response generation using Claude
✅ Genuine, helpful Reddit comments
✅ Tracks metrics and prevents duplicates
✅ Generates 3 responses (one for each target community)
✅ Rate limiting (60s between posts)

**Test Results:**
- Response quality: Excellent (authentic, helpful, natural)
- Personalization: High (adapts to specific situations)
- I MATCH mention: Subtle and appropriate

## Phase 2: Real Reddit Integration

To connect to actual Reddit and post automatically, you need:

### 1. Reddit API Credentials

**Get credentials (5 minutes):**
1. Go to https://www.reddit.com/prefs/apps
2. Click "create app" or "create another app"
3. Fill in:
   - Name: "I MATCH Recruiter"
   - Type: Select "script"
   - Description: "Helps people find professional services"
   - Redirect URI: http://localhost:8080
4. Click "create app"
5. Save these values:
   - **client_id**: (under the app name, looks like: `ABC123xyz`)
   - **client_secret**: (says "secret", looks like: `123456-abcdefg`)
   - **username**: Your Reddit username
   - **password**: Your Reddit password

### 2. Install PRAW (Reddit API Library)

```bash
ssh root@198.54.123.234
cd /root/agents/services/i-match-automation
source venv/bin/activate
pip install praw
```

### 3. Configure Credentials

```bash
# Add to .env file
echo "REDDIT_CLIENT_ID=your_client_id_here" >> .env
echo "REDDIT_CLIENT_SECRET=your_secret_here" >> .env
echo "REDDIT_USERNAME=your_username" >> .env
echo "REDDIT_PASSWORD=your_password" >> .env
```

### 4. Enable Phase 2 in Code

The autonomous_reddit_recruiter.py is already written to support Phase 2.
Just uncomment the PRAW integration sections (marked with "PHASE 2" comments).

**Two changes needed:**

**A. In `find_target_posts()` method:**
```python
# PHASE 2: Replace simulated posts with real Reddit search
import praw

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent="I MATCH Recruiter v1.0"
)

target_posts = []

# Search r/personalfinance
for post in reddit.subreddit("personalfinance").search(
    "financial advisor",
    time_filter="day",
    limit=10
):
    target_posts.append({
        "id": post.id,
        "subreddit": f"r/{post.subreddit.display_name}",
        "title": post.title,
        "body": post.selftext,
        "author": str(post.author),
        "url": f"https://reddit.com{post.permalink}",
        "created_utc": post.created_utc
    })

return target_posts
```

**B. In `post_comment()` method:**
```python
# PHASE 2: Actually post to Reddit
import praw

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent="I MATCH Recruiter v1.0"
)

# Get the submission
submission = reddit.submission(id=response['post_id'])

# Post comment
comment = submission.reply(response['generated_comment'])

print(f"✅ Posted comment: {comment.permalink}")
```

### 5. Run Continuously

```bash
# Run in background continuously
nohup python3 autonomous_reddit_recruiter.py --continuous > reddit_recruiter.log 2>&1 &

# Check it's running
ps aux | grep autonomous_reddit_recruiter

# View logs
tail -f reddit_recruiter.log

# Stop it
pkill -f autonomous_reddit_recruiter
```

## Important Notes:

### Reddit API Limits:
- **600 API calls per 10 minutes** (plenty for our use)
- **1 post per ~9 seconds** (we do 1 per 60 seconds, so safe)

### Best Practices:
- Start slow (1-2 responses per hour)
- Monitor karma (if negative, adjust approach)
- Respect subreddit rules (check each sub's posting guidelines)
- Be genuinely helpful (not just promotional)

### Monitoring Success:
```bash
# Check metrics
cat /root/agents/services/i-match-automation/data/reddit_outreach/recruitment_metrics.json

# See what was posted
ls -la /root/agents/services/i-match-automation/data/reddit_outreach/

# Track sign-ups from Reddit
curl http://198.54.123.234:8401/state | grep customers_total
```

## Expected Results:

**Week 1 (Phase 2 active):**
- 10-20 Reddit comments posted
- 1-3 people visit I MATCH
- 1 sign-up (goal)

**Month 1:**
- 100+ helpful comments
- 20-50 site visits
- 5-10 sign-ups
- First real customer → viral loop activated

## Current State:

Phase 1 is LIVE and generating high-quality responses.
You just need Reddit API credentials to enable Phase 2 posting.

**5-minute setup → Continuous autonomous customer acquisition**

No more manual work required.
