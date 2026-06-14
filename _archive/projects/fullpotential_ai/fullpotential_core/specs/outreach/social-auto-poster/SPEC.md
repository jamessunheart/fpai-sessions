# 📱 Social Auto-Poster System - Technical Specification

**Service Name:** `social-auto-poster`
**Purpose:** Autonomous daily posting to Twitter/LinkedIn without human intervention
**Priority:** Week 2-3 Build (High ROI)
**Infinite Scale:** Yes - posts forever, multiple platforms, zero effort

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Social Auto-Poster System                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐        ┌──────────────┐                  │
│  │ Cron Schedule│───────▶│Content Pool  │                  │
│  │  (8 AM daily)│        │(100+ posts)  │                  │
│  └──────────────┘        └──────┬───────┘                  │
│                                  │                           │
│                                  ▼                           │
│                         ┌─────────────────┐                 │
│                         │  AI Generator   │                 │
│                         │   (GPT-4 API)   │                 │
│                         └────────┬────────┘                 │
│                                  │                           │
│                    ┌─────────────┼─────────────┐            │
│                    ▼             ▼             ▼            │
│            ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│            │ Twitter  │  │ LinkedIn │  │ Facebook │        │
│            │   API    │  │   API    │  │   API    │        │
│            └──────────┘  └──────────┘  └──────────┘        │
│                                                              │
│                         ┌──────────────────┐                │
│                         │  Analytics DB    │                │
│                         │ (Track Results)  │                │
│                         └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 How It Works

### Daily Posting Flow
```
1. Cron triggers at 8 AM daily
2. System queries I MATCH metrics:
   - New customers today
   - Matches created today
   - Success stories
   - Interesting data points
3. AI generates 3 post variations:
   - Twitter version (280 chars)
   - LinkedIn version (longer, professional)
   - Facebook version (casual, visual)
4. Posts to all platforms via APIs
5. Tracks engagement metrics
6. Learns from performance (auto-optimization)
```

---

## 📝 Content Strategy

### Content Types (Rotated Daily)

**Type 1: $0 Marketing Challenge Update** (Daily for 30 days)
```
Template:
"📊 Day {day_number}: $0 Marketing Challenge

Today's results:
✅ {customer_count} new signups
✅ {match_count} matches created
✅ $0 spent on ads

What worked: {top_tactic}
Tomorrow's focus: {next_tactic}

Try it: https://fullpotential.com/get-matched

What would you try next? 👇"

Variables: Auto-filled from I MATCH database
```

**Type 2: Success Story** (When available)
```
Template:
"🎉 {customer_name} found their perfect {service_type} in 24 hours

Before: {problem}
After: {solution}

Match score: {match_score}%
Time saved: ~20 hours

See how it works: https://fullpotential.com/get-matched"

Source: I MATCH completed matches
```

**Type 3: Controversial Take** (Weekly)
```
Pool of 20+ hot takes:
- "Spending 30+ hours researching is a waste"
- "Generic marketplaces are dead"
- "AI > 20 hours of Googling"
- "Stop browsing, start matching"

Rotates through pool
```

**Type 4: Data Insight** (Weekly)
```
Template:
"📊 Interesting data from {total_matches} matches:

• {insight_1}
• {insight_2}
• {insight_3}

The average customer saves {hours_saved} hours.

Try matching: https://fullpotential.com/get-matched"

Source: I MATCH analytics
```

**Type 5: Educational** (2x week)
```
Topics:
- "How to choose an executive coach"
- "Church formation: 501c3 vs 508c1a"
- "Vetting AI developers: red flags"
- "What makes a good consultant?"

Evergreen content, rotates
```

---

## 🔧 Technical Implementation

### Stack
```python
# Core
FastAPI==0.104.1
APScheduler==3.10.4
SQLAlchemy==2.0.23
Redis==5.0.1

# AI
openai==1.3.0  # GPT-4 for content generation

# Social APIs
tweepy==4.14.0  # Twitter API v2
linkedin-api==2.0.0  # LinkedIn
facebook-sdk==3.1.0  # Facebook

# Monitoring
prometheus-client==0.19.0
sentry-sdk==1.38.0
```

### Directory Structure
```
social-auto-poster/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app
│   ├── scheduler.py          # APScheduler config
│   ├── content/
│   │   ├── __init__.py
│   │   ├── generator.py      # AI content generation
│   │   ├── templates.py      # Content templates
│   │   └── pool.py           # Pre-written content pool
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── twitter.py        # Twitter API integration
│   │   ├── linkedin.py       # LinkedIn API integration
│   │   └── facebook.py       # Facebook API integration
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── tracker.py        # Track post performance
│   │   └── optimizer.py      # Auto-optimize based on data
│   └── models/
│       ├── __init__.py
│       ├── post.py           # Post model
│       └── metrics.py        # Metrics model
├── tests/
├── docker-compose.yml
└── requirements.txt
```

### Database Schema
```sql
-- Posts log
CREATE TABLE social_posts (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,  -- 'twitter', 'linkedin', 'facebook'
    content TEXT NOT NULL,
    content_type VARCHAR(50),  -- 'challenge_update', 'success_story', etc.
    posted_at TIMESTAMP DEFAULT NOW(),
    platform_post_id VARCHAR(255),  -- ID from platform
    url TEXT,  -- URL of post
    metrics JSONB  -- impressions, engagements, clicks, etc.
);

-- Content performance tracking
CREATE TABLE content_performance (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL,
    template_id VARCHAR(100),
    platform VARCHAR(50),
    impressions INTEGER DEFAULT 0,
    engagements INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    engagement_rate FLOAT,
    click_rate FLOAT,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Posting schedule
CREATE TABLE posting_schedule (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    time TIME NOT NULL,  -- When to post (e.g., '08:00:00')
    timezone VARCHAR(50) DEFAULT 'America/Los_Angeles',
    enabled BOOLEAN DEFAULT TRUE,
    UNIQUE(platform, time)
);

-- Indexes
CREATE INDEX idx_posts_platform ON social_posts(platform);
CREATE INDEX idx_posts_posted_at ON social_posts(posted_at);
CREATE INDEX idx_performance_type ON content_performance(content_type);
```

---

## 📱 Platform Integration

### Twitter API v2
```python
import tweepy

class TwitterPoster:
    def __init__(self, api_key, api_secret, access_token, access_secret):
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )

    def post(self, content: str, url: str = None) -> dict:
        """Post to Twitter"""
        # Twitter automatically unfurls URLs
        tweet_text = f"{content}\n\n{url}" if url else content

        # Ensure within 280 char limit
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        response = self.client.create_tweet(text=tweet_text)

        return {
            "post_id": response.data['id'],
            "url": f"https://twitter.com/user/status/{response.data['id']}"
        }
```

### LinkedIn API
```python
from linkedin_api import Linkedin

class LinkedInPoster:
    def __init__(self, access_token):
        self.api = Linkedin('', '', access_token=access_token)

    def post(self, content: str, url: str = None) -> dict:
        """Post to LinkedIn"""
        post_data = {
            "author": f"urn:li:person:{self.get_profile_id()}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "ARTICLE" if url else "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        if url:
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                "status": "READY",
                "originalUrl": url
            }]

        response = self.api.post_share(post_data)
        return {"post_id": response['id']}
```

---

## 🤖 AI Content Generation

### GPT-4 Integration
```python
from openai import OpenAI

class ContentGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate_post(self, content_type: str, data: dict, platform: str) -> str:
        """Generate platform-specific content using GPT-4"""

        # Platform-specific constraints
        char_limits = {
            "twitter": 280,
            "linkedin": 3000,
            "facebook": 5000
        }

        prompt = self._build_prompt(content_type, data, platform, char_limits[platform])

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a marketing copywriter creating engaging social media posts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content

    def _build_prompt(self, content_type: str, data: dict, platform: str, char_limit: int) -> str:
        """Build GPT-4 prompt based on content type"""

        if content_type == "challenge_update":
            return f"""
            Create a {platform} post for the $0 Marketing Challenge update.

            Data:
            - Day: {data['day_number']}
            - New signups: {data['customer_count']}
            - Matches created: {data['match_count']}
            - Top tactic: {data['top_tactic']}

            Requirements:
            - {char_limit} characters max
            - Include URL: https://fullpotential.com/get-matched
            - Engaging, transparent tone
            - End with question to drive engagement
            - Use relevant emoji
            """

        # ... other content types
```

---

## ⏰ Posting Schedule

### APScheduler Configuration
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class PostingScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start scheduled posting"""

        # Twitter: 8 AM and 2 PM daily (PT)
        self.scheduler.add_job(
            self.post_to_twitter,
            CronTrigger(hour=8, minute=0, timezone='America/Los_Angeles'),
            id='twitter_morning'
        )
        self.scheduler.add_job(
            self.post_to_twitter,
            CronTrigger(hour=14, minute=0, timezone='America/Los_Angeles'),
            id='twitter_afternoon'
        )

        # LinkedIn: 8 AM daily (PT) - Professional audience
        self.scheduler.add_job(
            self.post_to_linkedin,
            CronTrigger(hour=8, minute=0, timezone='America/Los_Angeles'),
            id='linkedin_morning'
        )

        # Analytics: Update metrics every hour
        self.scheduler.add_job(
            self.update_metrics,
            CronTrigger(minute=0),  # Every hour
            id='metrics_update'
        )

        self.scheduler.start()
```

---

## 📊 Auto-Optimization

### Performance Tracking & Optimization
```python
class ContentOptimizer:
    def analyze_performance(self) -> dict:
        """Analyze which content types perform best"""

        query = """
        SELECT
            content_type,
            platform,
            AVG(engagement_rate) as avg_engagement,
            AVG(click_rate) as avg_clicks,
            COUNT(*) as posts_count
        FROM content_performance
        WHERE posted_at > NOW() - INTERVAL '30 days'
        GROUP BY content_type, platform
        ORDER BY avg_engagement DESC
        """

        results = db.execute(query)
        return results

    def optimize_posting_strategy(self):
        """Auto-adjust what content to post based on performance"""

        performance = self.analyze_performance()

        # Increase frequency of high-performing content
        for row in performance:
            if row['avg_engagement'] > 0.05:  # 5%+ engagement
                self.increase_frequency(row['content_type'], row['platform'])
            elif row['avg_engagement'] < 0.01:  # <1% engagement
                self.decrease_frequency(row['content_type'], row['platform'])

        # Auto-deprecate lowest performers
        bottom_10_percent = performance[-int(len(performance) * 0.1):]
        for row in bottom_10_percent:
            self.deprecate_content_type(row['content_type'])
```

---

## 🚀 Deployment

### Docker Compose
```yaml
version: '3.8'

services:
  social-poster-api:
    build: .
    ports:
      - "8501:8501"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TWITTER_API_KEY=${TWITTER_API_KEY}
      - LINKEDIN_ACCESS_TOKEN=${LINKEDIN_ACCESS_TOKEN}
    depends_on:
      - redis

  scheduler:
    build: .
    command: python -m app.scheduler
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TWITTER_API_KEY=${TWITTER_API_KEY}
      - LINKEDIN_ACCESS_TOKEN=${LINKEDIN_ACCESS_TOKEN}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## ✅ Success Criteria

### Week 1 (MVP)
- [ ] Posts to Twitter automatically at 8 AM daily
- [ ] Posts to LinkedIn automatically at 8 AM daily
- [ ] AI generates content from I MATCH data
- [ ] Metrics tracked in database

### Month 1 (Optimization)
- [ ] 60+ posts made (30 days × 2 platforms)
- [ ] 5%+ average engagement rate
- [ ] Auto-optimization working
- [ ] 100+ link clicks driven to form

### Month 3 (Scale)
- [ ] 3 platforms (added Facebook)
- [ ] 200+ posts made
- [ ] Content pool optimized
- [ ] 1000+ link clicks total

---

## 📈 Expected Impact

**Effort Saved:**
- Manual posting: 30 min/day = 15 hours/month
- Automated: 0 hours/month forever
- **Savings: 180 hours/year**

**Traffic Generated:**
- Conservative: 10 clicks/post × 60 posts/month = 600 visits/month
- Moderate: 20 clicks/post = 1,200 visits/month
- **Result: +15-30% traffic**

**Brand Building:**
- 60+ posts/month = consistent presence
- Engagement builds authority
- Compounds over time

---

**BUILD TIME:** 10-12 hours
**MAINTENANCE:** 0 hours/month
**INFINITE SCALE:** Yes - posts forever, multiple platforms, auto-optimizes

**Next:** Build after email automation (Week 2-3)
