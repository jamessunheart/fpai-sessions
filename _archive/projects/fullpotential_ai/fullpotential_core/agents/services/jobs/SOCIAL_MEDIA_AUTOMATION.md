# AI-Powered Social Media Recruitment Tool

**Built:** `social_media_recruiter.py`
**Purpose:** Autonomous recruitment via Twitter, LinkedIn, Reddit APIs
**Status:** Ready for API credentials

---

## What This Tool Does

### 1. Auto-Generate Optimized Posts
```python
from app.services.social_media_recruiter import social_media_recruiter

# AI generates platform-optimized content
twitter_post = await social_media_recruiter.generate_social_post(
    job=job_details,
    platform='twitter',
    style='viral'
)

# Returns:
{
  "content": "🤖 Not another AI wrapper...",
  "hashtags": ["ai", "hiring", "crypto"],
  "thread": ["Tweet 1", "Tweet 2", "Tweet 3"],
  "best_time_to_post": "Tuesday 10am ET",
  "engagement_strategy": "Respond to all questions within 1 hour"
}
```

### 2. Auto-Post to Social Media
```python
# Post directly to Twitter
result = await social_media_recruiter.post_to_twitter(
    content=twitter_post['content'],
    job_url=job_url
)

# Returns:
{
  "status": "success",
  "tweet_id": "1234567890",
  "url": "https://twitter.com/user/status/1234567890"
}
```

### 3. Find Developers Automatically
```python
# Search Twitter for developers with required skills
candidates = await social_media_recruiter.find_developers_on_twitter(
    skills=["Python", "FastAPI", "React"],
    location="remote"
)

# Returns 50 potential candidates:
[
  {
    "username": "dev_jane",
    "bio": "Full-stack dev | Python | React | AI enthusiast",
    "profile_url": "https://twitter.com/dev_jane",
    "match_score": 0.85
  },
  ...
]
```

### 4. Generate Personalized Outreach
```python
# AI generates personalized DM
dm = await social_media_recruiter.generate_outreach_dm(
    candidate=candidate_profile,
    job=job_details
)

# Returns:
"Hi Jane! Saw your recent tweet about building with Claude API.
We're hiring for an AI infrastructure role that seems perfect for you.
Unique opportunity: AI interviews, crypto payments, autonomous systems.
Interested? http://..."
```

### 5. Monitor Engagement
```python
# Track post performance
metrics = await social_media_recruiter.monitor_engagement(
    post_id=tweet_id,
    platform='twitter'
)

# Returns:
{
  "views": 10500,
  "likes": 342,
  "shares": 87,
  "applications_attributed": 12,
  "requires_attention": [
    "Comment from @dev123 asking about tech stack",
    "DM from @engineer456 expressing interest"
  ]
}
```

---

## Setup Required

### API Credentials Needed

**Twitter API v2** (Required for posting/searching)
```bash
# Get from: https://developer.twitter.com/
export TWITTER_BEARER_TOKEN="your_bearer_token"
export TWITTER_API_KEY="your_api_key"
export TWITTER_API_SECRET="your_api_secret"
export TWITTER_ACCESS_TOKEN="your_access_token"
export TWITTER_ACCESS_SECRET="your_access_secret"
```

**LinkedIn API** (Optional - for professional reach)
```bash
# Get from: https://www.linkedin.com/developers/
export LINKEDIN_ACCESS_TOKEN="your_access_token"
export LINKEDIN_PERSON_URN="urn:li:person:YOUR_ID"
```

**Reddit API** (Optional - for community posts)
```bash
# Get from: https://www.reddit.com/prefs/apps
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USERNAME="your_username"
export REDDIT_PASSWORD="your_password"
```

**Anthropic API** (Already have - for AI content generation)
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## How to Set Up Twitter API (Fastest Path)

### Step 1: Create Twitter Developer Account
1. Go to https://developer.twitter.com/
2. Sign in with your Twitter account
3. Apply for "Elevated" access (free)
4. Fill out the form (select "Building tools for other businesses")

### Step 2: Create App
1. In developer portal, click "Create App"
2. Name it: "Full Potential AI Recruiter"
3. Get your credentials:
   - API Key
   - API Secret
   - Bearer Token
   - Access Token
   - Access Secret

### Step 3: Set Permissions
1. In app settings, go to "User authentication settings"
2. Enable: "Read and Write" permissions
3. Save

### Step 4: Add to System
```bash
# On server
ssh root@198.54.123.234
echo "TWITTER_BEARER_TOKEN=..." >> /root/agents/services/jobs/.env
echo "TWITTER_API_KEY=..." >> /root/agents/services/jobs/.env
echo "TWITTER_API_SECRET=..." >> /root/agents/services/jobs/.env

# Restart jobs service
docker restart fpai-jobs
```

**Timeline:** 30 minutes to full setup

---

## Autonomous Recruitment Workflow

### Phase 1: Auto-Post Jobs
```
New Job Created
    ↓
AI Generates Optimized Post
    ↓
Auto-Post to Twitter, LinkedIn, Reddit
    ↓
Monitor Engagement
    ↓
Respond to Comments (AI-generated responses)
    ↓
Track Applications by Source
```

### Phase 2: Proactive Outreach
```
System Needs: Python Developer
    ↓
Search Twitter for "Python developer"
    ↓
Find 50 Candidates
    ↓
AI Scores Each (based on bio, tweets, fit)
    ↓
Generate Personalized DMs (top 20)
    ↓
Send DMs (with human approval)
    ↓
Track Responses
    ↓
Nudge If No Response (after 48h)
```

### Phase 3: Community Engagement
```
Monitor AI/Developer Communities
    ↓
Identify Relevant Discussions
    ↓
AI Generates Helpful Comments
    ↓
Subtly Mention We're Hiring
    ↓
Direct Interested People to Jobs Board
```

---

## Start Simple, Scale Up

### Week 1: Manual Posting with AI Content
```python
# Generate post
post = await social_media_recruiter.generate_social_post(job, 'twitter')

# You manually copy/paste to Twitter
print(post['content'])
```

**Benefit:** Get AI-optimized content instantly

### Week 2: Auto-Posting
```python
# Fully automated
result = await social_media_recruiter.post_to_twitter(
    content=post['content'],
    job_url=job_url
)

# Job automatically posted to Twitter
```

**Benefit:** No manual posting needed

### Week 3: Proactive Search
```python
# Find developers automatically
candidates = await social_media_recruiter.find_developers_on_twitter(
    skills=job['skills']
)

# Generate personalized outreach
for candidate in candidates[:10]:
    dm = await social_media_recruiter.generate_outreach_dm(candidate, job)
    # Review DM, approve sending
```

**Benefit:** Find passive candidates

### Week 4: Full Automation
```python
# Complete autonomous loop
- Post job automatically
- Search for candidates
- Generate + send DMs
- Monitor responses
- Engage with comments
- Track applications
```

**Benefit:** Fully autonomous recruitment

---

## Integration with Hiring System

### Workflow
```
1. Post Job → social_media_recruiter.post_to_twitter()
2. Find Candidates → social_media_recruiter.find_developers()
3. DM Candidates → social_media_recruiter.generate_outreach_dm()
4. They Apply → Jobs Board
5. AI Screens → ai_screener.py
6. AI Interviews → ai_interviewer.py
7. Human Approves → You
8. AI Coordinates → labor_coordinator.py
9. AI Verifies → milestone_verifier.py
10. Payment Released → Smart contract
```

**Human involvement:** Steps 7 only (final approval)
**Everything else:** Automated

---

## Compliance & Best Practices

### Rate Limits
- Twitter: 300 tweets/3 hours, 1000 DMs/day
- LinkedIn: 100 posts/day
- Reddit: Varies by subreddit

**Our approach:**
- Respect limits
- Space out posts
- Quality over quantity

### Spam Prevention
- Only DM people who showed interest
- Personalized messages (AI-generated but genuine)
- One follow-up max
- Respect "not interested" immediately

### Content Quality
- AI generates, human can review
- A/B test what performs best
- Authentic, not salesy
- Community value first

---

## Metrics to Track

### Engagement
- Views per post
- Likes/shares
- Comments
- Click-through rate to jobs board

### Conversion
- Applications per post
- Source attribution (which platform)
- Quality of candidates by source
- Cost per application

### ROI
- Time saved vs manual posting
- Quality of hires from social
- Engagement rate improvement over time

---

## Next Steps to Get Started

### Option 1: Quick Start (Today)
1. Generate AI content for existing job
2. Manually post to your Twitter
3. See engagement
4. Iterate

### Option 2: Semi-Automated (This Week)
1. Set up Twitter API credentials (30 min)
2. Auto-post jobs to Twitter
3. Monitor engagement manually
4. Reply to comments with AI suggestions

### Option 3: Full Automation (Next Week)
1. Set up all API credentials
2. Auto-post to multiple platforms
3. Search for candidates automatically
4. Generate personalized outreach
5. Track everything

---

## The Vision

**Instead of:**
- Manually posting to social media
- Manually searching for candidates
- Manually writing personalized messages
- Manually tracking engagement

**You get:**
- AI generates optimized content
- AI posts to all platforms
- AI finds qualified candidates
- AI writes personalized outreach
- AI tracks everything
- You just approve final hiring decisions

**Time saved:** 10 hours/week → 30 minutes/week

---

## API Credential Priority

**Essential (Start here):**
1. ✅ Anthropic API (already have)
2. 🔲 Twitter API v2 (30 min setup)

**High Value:**
3. 🔲 LinkedIn API (2 hours setup)

**Nice to Have:**
4. 🔲 Reddit API (1 hour setup)

**Start with Twitter - biggest developer audience, easiest API**

---

## Ready to Set Up?

**Next action:** Get Twitter API credentials

1. Go to https://developer.twitter.com/
2. Apply for access (free, ~10 min approval)
3. Create app and get credentials
4. Add to `.env` file
5. Test with one job post
6. Scale from there

**Want me to walk you through Twitter API setup step-by-step?**

Or should I focus on a different social platform first?

🚀 Let's automate recruitment!
