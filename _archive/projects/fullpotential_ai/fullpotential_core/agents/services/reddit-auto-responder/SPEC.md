# Reddit Auto-Responder - Technical Specification

**Service:** reddit-auto-responder
**Type:** Autonomous Machine (24/7 engagement)
**Priority:** MEDIUM (Week 4-5)
**Build Time:** 10 hours
**Impact:** Infinite passive leads, thought leadership, zero spam risk

---

## 🎯 Mission

Monitor relevant subreddits 24/7. Detect opportunities to provide genuine value. Post helpful, non-promotional comments that establish expertise. Generate passive leads forever without being spammy.

---

## 💰 Business Impact

### The Value-First Strategy

**NOT this:** "Check out our service at fullpotential.com"
**THIS:** Provide genuinely helpful answer, mention our platform naturally in context

**Example:**
```
r/pastors: "Our church is struggling with declining attendance..."

Our response:
"I've seen this pattern often - usually it's a combination of unclear messaging and lack of digital presence. Here's what's worked:

1. Audit your church's value proposition (are you clear on WHO you serve?)
2. Invest in digital outreach (website, social media consistency)
3. Focus on retention first (exit surveys help identify why people leave)

If you want structured help, platforms like Full Potential AI match churches with experienced growth consultants (I'm not affiliated, just seen good results). But honestly, starting with those 3 steps will tell you a lot.

Happy to discuss further if helpful!"
```

**Result:** Helpful → upvotes → visibility → trust → leads

### Revenue Impact
- **50 valuable comments/week = 200/month**
- **10% generate follow-up DMs = 20 conversations/month**
- **25% of conversations → leads = 5 qualified leads/month**
- **20% close rate = 1 customer/month**
- **$2,500 avg value = $2,500/month**
- **Annual value: $30,000**

### Strategic Value
- Thought leadership positioning
- Zero cost (vs $5+ per click on ads)
- Compounding (old comments continue working)
- Community building
- Market research (understand pain points)

---

## 🏗️ Architecture

### Tech Stack
- **Framework:** FastAPI (async)
- **Reddit API:** PRAW (Python Reddit API Wrapper)
- **Database:** PostgreSQL (comment tracking, karma scores)
- **LLM:** GPT-4 (for response generation)
- **Scheduling:** APScheduler (continuous monitoring)
- **Monitoring:** Prometheus + Sentry

### System Flow
```
┌──────────────────────────────────────────────┐
│  Reddit Auto-Responder                       │
├──────────────────────────────────────────────┤
│                                              │
│  1. Subreddit Monitor                        │
│     - Track 20+ relevant subreddits          │
│     - Stream new posts in real-time          │
│     - Filter by keywords + sentiment         │
│     - Prioritize by engagement potential     │
│                                              │
│  2. Opportunity Scorer                       │
│     - Analyze post for relevance             │
│     - Check author credibility               │
│     - Estimate upvote potential              │
│     - Assign priority score                  │
│                                              │
│  3. Response Generator (GPT-4)               │
│     - Generate helpful, value-first response │
│     - Natural mention of Full Potential AI   │
│     - Appropriate tone for subreddit         │
│     - Include actionable advice              │
│                                              │
│  4. Human-in-Loop (Optional)                 │
│     - Queue responses for review             │
│     - Auto-post high-confidence (score >0.8) │
│     - Manual review medium-confidence        │
│     - Skip low-confidence (<0.5)             │
│                                              │
│  5. Performance Tracker                      │
│     - Track karma per comment                │
│     - Monitor DM conversations               │
│     - Detect shadowbans / rate limits        │
│     - Learn from high-performing comments    │
│                                              │
└──────────────────────────────────────────────┘
```

---

## 📋 Target Subreddits

### Primary Targets (High Value)
```python
SUBREDDITS = [
    # Church leadership
    "pastors",           # 45K members, very active
    "Christianity",      # 380K members, huge reach
    "OpenChristian",     # 50K members, progressive
    "Reformed",          # 65K members, theological

    # Nonprofits
    "nonprofit",         # 25K members, perfect audience
    "Fundraising",       # 8K members, specific needs

    # Small business (churches as orgs)
    "smallbusiness",     # 1.8M members, massive
    "Entrepreneur",      # 3.2M members, growth-minded

    # Coaching/consulting
    "consulting",        # 35K members, industry peers
    "businessanalysis",  # 30K members, adjacent

    # Ministry-specific
    "youthministry",     # 5K members, niche
    "worshipleaders",    # 3K members, niche
]
```

### Keyword Triggers
```python
KEYWORDS = {
    "high_priority": [
        "need a coach",
        "looking for consultant",
        "struggling with growth",
        "church attendance declining",
        "need help with",
        "recommendations for",
    ],
    "medium_priority": [
        "church growth",
        "leadership development",
        "pastor burnout",
        "volunteer management",
        "ministry strategy",
        "church revitalization",
    ],
    "low_priority": [
        "advice",
        "thoughts on",
        "anyone experienced with",
    ]
}
```

---

## 🤖 Response Generation

### GPT-4 Prompt Template
```python
REDDIT_RESPONSE_PROMPT = """
You are a helpful expert in church leadership and ministry consulting. A Reddit user posted the following in r/{subreddit}:

POST TITLE: {title}
POST BODY: {body}
SUBREDDIT CONTEXT: {subreddit_description}

Generate a helpful, genuine response that:
1. Directly addresses their question/problem
2. Provides 2-3 actionable pieces of advice
3. Shows expertise without being preachy
4. Mentions Full Potential AI ONLY if naturally relevant (don't force it)
5. Offers to discuss further if they want
6. Uses appropriate tone for r/{subreddit} (professional but warm)

CRITICAL:
- Be helpful FIRST, promotional NEVER (unless it genuinely helps)
- If Full Potential AI doesn't fit naturally, don't mention it
- Focus on value, not selling
- Keep it 150-250 words (Reddit-appropriate length)

Output JSON:
{{
  "response": "...",
  "confidence": 0.85,  # How confident this is helpful (0-1)
  "mentions_fpai": true/false,
  "estimated_value": "high | medium | low"
}}
"""
```

### Response Quality Checks
```python
async def validate_response(response: str, post: Dict) -> Dict:
    """Validate response meets quality standards"""

    checks = {
        # Length check
        "appropriate_length": 100 <= len(response.split()) <= 300,

        # Value check
        "provides_actionable_advice": has_numbered_list(response) or has_specific_recommendations(response),

        # Tone check
        "not_overly_promotional": response.count("Full Potential") <= 1,

        # Spam check
        "no_direct_links": "http" not in response or "fullpotential.com" not in response,

        # Relevance check
        "addresses_question": calculate_relevance(response, post['body']) > 0.6,

        # Natural check
        "sounds_human": not has_ai_tells(response),  # No "as an AI...", etc.
    }

    return {
        "passes": all(checks.values()),
        "score": sum(checks.values()) / len(checks),
        "failed_checks": [k for k, v in checks.items() if not v]
    }
```

---

## 📊 Opportunity Scoring

### Scoring Algorithm
```python
class OpportunityScorer:
    """Score Reddit posts for engagement potential"""

    async def score_post(self, post) -> float:
        """Return score 0-1 indicating response priority"""

        score = 0.0

        # Recency (newer = better)
        age_hours = (datetime.now() - post.created_utc).total_seconds() / 3600
        if age_hours < 2:
            score += 0.3  # Fresh post, high visibility if we respond now
        elif age_hours < 6:
            score += 0.2
        elif age_hours < 24:
            score += 0.1
        else:
            return 0.0  # Too old, skip

        # Keyword match strength
        body_lower = post.selftext.lower()
        if any(kw in body_lower for kw in KEYWORDS['high_priority']):
            score += 0.4
        elif any(kw in body_lower for kw in KEYWORDS['medium_priority']):
            score += 0.25
        elif any(kw in body_lower for kw in KEYWORDS['low_priority']):
            score += 0.1

        # Author credibility (avoid trolls)
        if post.author.link_karma > 1000 and post.author.comment_karma > 1000:
            score += 0.1
        elif post.author.link_karma < 10:
            score -= 0.2  # Possible throwaway account

        # Subreddit size (bigger = more visibility)
        if post.subreddit.subscribers > 100000:
            score += 0.15
        elif post.subreddit.subscribers > 10000:
            score += 0.1
        else:
            score += 0.05

        # Engagement (more comments = more eyes)
        if post.num_comments < 5:
            score += 0.15  # Early, can be top comment
        elif post.num_comments < 20:
            score += 0.1
        else:
            score += 0.05  # Crowded, less visibility

        return min(1.0, max(0.0, score))
```

---

## 🔄 Monitoring Loop

### Continuous Monitoring
```python
from praw import Reddit
from apscheduler.schedulers.asyncio import AsyncIOScheduler

reddit = Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="FullPotentialBot/1.0",
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD
)

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=15)
async def monitor_subreddits():
    """Check subreddits for new opportunities every 15 minutes"""

    for subreddit_name in SUBREDDITS:
        subreddit = reddit.subreddit(subreddit_name)

        # Get new posts from last 2 hours
        for post in subreddit.new(limit=25):
            age_hours = (datetime.now() - datetime.fromtimestamp(post.created_utc)).total_seconds() / 3600

            if age_hours > 2:
                continue  # Skip old posts

            # Check if already responded
            if await db.fetch_one("SELECT id FROM responses WHERE reddit_post_id = $1", post.id):
                continue  # Already responded

            # Score opportunity
            score = await scorer.score_post(post)

            if score < 0.5:
                logger.debug(f"⏭️  Skipped (low score {score:.2f}): {post.title}")
                continue

            # Generate response
            response_data = await generator.generate_response(post)

            # Validate response
            validation = await validate_response(response_data['response'], post)

            if not validation['passes']:
                logger.warning(f"❌ Response failed validation: {validation['failed_checks']}")
                continue

            # Decide: auto-post or queue for review
            if response_data['confidence'] > 0.8 and score > 0.7:
                # High confidence + high opportunity = auto-post
                await post_comment(post, response_data['response'])
                logger.info(f"✅ Auto-posted to r/{subreddit_name}: {post.title}")
            else:
                # Queue for human review
                await queue_for_review(post, response_data, score)
                logger.info(f"📋 Queued for review: {post.title}")
```

### Posting Function
```python
async def post_comment(post, response_text: str):
    """Post comment to Reddit and track in database"""

    try:
        # Post comment
        comment = post.reply(response_text)

        # Track in database
        await db.execute("""
            INSERT INTO responses (
                reddit_post_id,
                reddit_comment_id,
                subreddit,
                post_title,
                response_text,
                confidence_score,
                posted_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, post.id, comment.id, str(post.subreddit), post.title, response_text, 0.85)

        return comment

    except Exception as e:
        logger.error(f"Failed to post comment: {e}")
        raise
```

---

## 📈 Performance Tracking

### Karma Tracking
```python
@scheduler.scheduled_job('cron', hour='*/6')  # Every 6 hours
async def update_comment_karma():
    """Update karma scores for all our comments"""

    comments = await db.fetch_all("""
        SELECT reddit_comment_id, id
        FROM responses
        WHERE posted_at > NOW() - INTERVAL '30 days'
    """)

    for row in comments:
        try:
            comment = reddit.comment(id=row['reddit_comment_id'])
            comment.refresh()

            # Update karma in database
            await db.execute("""
                UPDATE responses
                SET
                    karma_score = $1,
                    num_replies = $2,
                    last_checked = NOW()
                WHERE id = $3
            """, comment.score, len(comment.replies), row['id'])

        except Exception as e:
            logger.error(f"Failed to refresh comment {row['reddit_comment_id']}: {e}")

    logger.info(f"♻️  Updated karma for {len(comments)} comments")
```

### DM Monitoring
```python
@scheduler.scheduled_job('interval', minutes=30)
async def check_direct_messages():
    """Check for DMs from Reddit users"""

    for message in reddit.inbox.unread(limit=None):
        if message.was_comment:
            continue  # Skip comment replies, we want DMs

        # Log DM
        await db.execute("""
            INSERT INTO reddit_dms (
                sender_username,
                subject,
                body,
                received_at,
                status
            ) VALUES ($1, $2, $3, NOW(), 'unread')
        """, message.author.name, message.subject, message.body)

        # Mark as read
        message.mark_read()

        # Notify human
        await notify_slack(f"📬 New Reddit DM from u/{message.author.name}: {message.subject}")

        logger.info(f"📬 New DM from u/{message.author.name}")
```

### Learning from Performance
```python
async def analyze_top_performers():
    """Find patterns in high-performing comments"""

    top_comments = await db.fetch_all("""
        SELECT *
        FROM responses
        WHERE karma_score >= 10
        ORDER BY karma_score DESC
        LIMIT 20
    """)

    patterns = {
        "avg_length": statistics.mean(len(c['response_text'].split()) for c in top_comments),
        "common_phrases": extract_common_phrases(top_comments),
        "avg_mention_rate": sum(1 for c in top_comments if "Full Potential" in c['response_text']) / len(top_comments),
        "best_subreddits": Counter(c['subreddit'] for c in top_comments).most_common(5),
    }

    logger.info(f"📊 Top performer analysis: {patterns}")

    # Use patterns to improve future responses
    # (feed into GPT-4 prompt as examples)
```

---

## 🗄️ Database Schema

```sql
CREATE TABLE responses (
    id SERIAL PRIMARY KEY,
    reddit_post_id VARCHAR(20) UNIQUE NOT NULL,
    reddit_comment_id VARCHAR(20),
    subreddit VARCHAR(100),

    -- Post info
    post_title TEXT,
    post_body TEXT,
    post_author VARCHAR(100),

    -- Response
    response_text TEXT,
    confidence_score DECIMAL(3,2),

    -- Performance
    karma_score INTEGER DEFAULT 0,
    num_replies INTEGER DEFAULT 0,
    generated_dm BOOLEAN DEFAULT FALSE,

    -- Metadata
    posted_at TIMESTAMP DEFAULT NOW(),
    last_checked TIMESTAMP,
    status VARCHAR(20) DEFAULT 'posted'  -- posted | deleted | shadowbanned
);

CREATE TABLE reddit_dms (
    id SERIAL PRIMARY KEY,
    sender_username VARCHAR(100),
    subject TEXT,
    body TEXT,
    received_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'unread',  -- unread | responded | converted
    response_id INTEGER REFERENCES responses(id)
);

CREATE TABLE review_queue (
    id SERIAL PRIMARY KEY,
    reddit_post_id VARCHAR(20),
    subreddit VARCHAR(100),
    post_title TEXT,
    suggested_response TEXT,
    confidence_score DECIMAL(3,2),
    opportunity_score DECIMAL(3,2),
    queued_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    action VARCHAR(20)  -- posted | skipped | edited_then_posted
);

CREATE INDEX idx_responses_subreddit ON responses(subreddit);
CREATE INDEX idx_responses_posted_at ON responses(posted_at);
CREATE INDEX idx_responses_karma ON responses(karma_score);
```

---

## 🛡️ Anti-Spam Safeguards

### Rate Limiting
```python
class RateLimiter:
    """Prevent Reddit from flagging us as spam"""

    MAX_COMMENTS_PER_HOUR = 5
    MAX_COMMENTS_PER_DAY = 30
    MIN_MINUTES_BETWEEN_COMMENTS = 10

    async def can_post(self) -> bool:
        """Check if we can post without hitting rate limits"""

        # Check last hour
        last_hour_count = await db.fetch_val("""
            SELECT COUNT(*)
            FROM responses
            WHERE posted_at > NOW() - INTERVAL '1 hour'
        """)

        if last_hour_count >= self.MAX_COMMENTS_PER_HOUR:
            logger.warning("⚠️  Rate limit: too many comments in last hour")
            return False

        # Check last day
        last_day_count = await db.fetch_val("""
            SELECT COUNT(*)
            FROM responses
            WHERE posted_at > NOW() - INTERVAL '1 day'
        """)

        if last_day_count >= self.MAX_COMMENTS_PER_DAY:
            logger.warning("⚠️  Rate limit: too many comments today")
            return False

        # Check time since last comment
        last_comment_time = await db.fetch_val("""
            SELECT posted_at
            FROM responses
            ORDER BY posted_at DESC
            LIMIT 1
        """)

        if last_comment_time:
            minutes_since = (datetime.now() - last_comment_time).total_seconds() / 60
            if minutes_since < self.MIN_MINUTES_BETWEEN_COMMENTS:
                logger.debug(f"⏳ Waiting {self.MIN_MINUTES_BETWEEN_COMMENTS - minutes_since:.1f} more minutes")
                return False

        return True
```

### Shadowban Detection
```python
@scheduler.scheduled_job('cron', hour=12)  # Daily at noon
async def check_for_shadowban():
    """Detect if our account is shadowbanned"""

    # Get recent comment
    recent = await db.fetch_one("""
        SELECT reddit_comment_id, subreddit
        FROM responses
        WHERE posted_at > NOW() - INTERVAL '24 hours'
        ORDER BY posted_at DESC
        LIMIT 1
    """)

    if not recent:
        return  # No recent comments to check

    try:
        # Try to fetch comment from Reddit
        comment = reddit.comment(id=recent['reddit_comment_id'])
        comment.refresh()

        # If we can fetch it, we're not shadowbanned
        logger.info("✅ Shadowban check: OK")

    except Exception as e:
        # If we can't fetch it, possible shadowban
        logger.error(f"🚨 POSSIBLE SHADOWBAN: {e}")
        await notify_slack("🚨 Reddit bot may be shadowbanned! Check manually.")
```

---

## 🚀 Deployment

### Docker Compose
```yaml
version: '3.8'

services:
  reddit-bot:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/fpai
      - REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
      - REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}
      - REDDIT_USERNAME=${REDDIT_USERNAME}
      - REDDIT_PASSWORD=${REDDIT_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Systemd Service
```ini
[Unit]
Description=Reddit Auto-Responder Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/fpai/reddit-auto-responder
ExecStart=/usr/bin/docker-compose up
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

---

## 📊 Dashboard

### Admin Dashboard (FastAPI)
```python
@app.get("/dashboard")
async def dashboard():
    """Admin dashboard for Reddit bot performance"""

    # Stats
    stats = {
        "total_comments": await db.fetch_val("SELECT COUNT(*) FROM responses"),
        "total_karma": await db.fetch_val("SELECT SUM(karma_score) FROM responses"),
        "total_dms": await db.fetch_val("SELECT COUNT(*) FROM reddit_dms"),
        "avg_karma": await db.fetch_val("SELECT AVG(karma_score) FROM responses"),
        "top_subreddits": await db.fetch_all("""
            SELECT subreddit, COUNT(*) as count, AVG(karma_score) as avg_karma
            FROM responses
            GROUP BY subreddit
            ORDER BY avg_karma DESC
            LIMIT 5
        """),
        "recent_comments": await db.fetch_all("""
            SELECT *
            FROM responses
            ORDER BY posted_at DESC
            LIMIT 10
        """),
        "review_queue_size": await db.fetch_val("SELECT COUNT(*) FROM review_queue WHERE reviewed_at IS NULL"),
    }

    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})
```

---

## ✅ Success Criteria

### Functional Requirements
- ✅ Monitor 20+ subreddits 24/7
- ✅ Generate helpful, value-first responses
- ✅ Post 20-30 comments per week
- ✅ Zero spam flags or bans
- ✅ Track karma and DM conversions
- ✅ Human review queue for medium-confidence posts

### Quality Requirements
- ✅ Average karma >5 per comment
- ✅ <5% deleted/downvoted comments
- ✅ >50% mention Full Potential AI naturally
- ✅ Zero "stop spamming" complaints
- ✅ Comments sound genuinely helpful (not AI-generated)

### Business Requirements
- ✅ 5+ qualified leads/month from Reddit by Month 3
- ✅ 10+ qualified leads/month by Month 6
- ✅ 1+ customer/month from Reddit by Month 6
- ✅ $2,500+/month revenue from Reddit by Month 12
- ✅ Positive brand perception (upvotes > downvotes)

---

## 🧪 Testing

### Unit Tests
```python
async def test_opportunity_scoring():
    """Test post scoring algorithm"""
    post = create_mock_post(
        title="Need church growth advice",
        body="Our attendance is declining...",
        age_hours=1,
        num_comments=2
    )

    score = await scorer.score_post(post)
    assert score >= 0.7  # Should be high priority

async def test_response_generation():
    """Test GPT-4 response quality"""
    post = create_mock_post(
        title="Looking for a ministry coach",
        body="Our church needs help with leadership development"
    )

    response = await generator.generate_response(post)
    assert len(response['response'].split()) >= 100
    assert response['confidence'] > 0.5
    assert not is_spammy(response['response'])

async def test_rate_limiting():
    """Test rate limiter prevents spam"""
    # Post 5 comments in last hour
    await post_mock_comments(5)

    can_post = await rate_limiter.can_post()
    assert can_post is False  # Should block 6th comment
```

---

## 📈 Expected Growth

### Month 1
- **Comments posted:** 60
- **Avg karma per comment:** 3
- **Total karma:** 180
- **DMs received:** 5
- **Leads:** 1-2

### Month 3
- **Comments posted:** 200
- **Avg karma per comment:** 5
- **Total karma:** 1,000
- **DMs received:** 20
- **Leads:** 5-10
- **Customers:** 1

### Month 6
- **Comments posted:** 400
- **Avg karma per comment:** 7
- **Total karma:** 2,800
- **DMs received:** 50
- **Leads:** 10-15
- **Customers:** 2-3

### Month 12
- **Comments posted:** 800
- **Avg karma per comment:** 10
- **Total karma:** 8,000
- **DMs received:** 100
- **Leads:** 20-30
- **Customers:** 5-10
- **Revenue:** $12,500-25,000

### Infinite Horizon
- Old comments continue getting upvotes/visibility
- Build reputation as helpful expert
- Reddit karma → social proof
- Comments rank in Google (Reddit has high SEO authority)
- **INFINITE PASSIVE LEADS**

---

## 🔗 Integration Points

### With I MATCH System
```python
# When DM converts to lead
async def convert_reddit_dm_to_customer(dm_id: int, user_data: Dict):
    """Create customer from Reddit DM"""

    customer_id = await db.fetch_val("""
        INSERT INTO customers (
            name,
            email,
            service_type,
            needs_description,
            acquisition_source,
            acquisition_details
        ) VALUES ($1, $2, $3, $4, 'reddit', $5)
        RETURNING id
    """, user_data['name'], user_data['email'], user_data['service_type'],
         user_data['needs'], f"Reddit DM from u/{user_data['reddit_username']}")

    # Mark DM as converted
    await db.execute("UPDATE reddit_dms SET status = 'converted' WHERE id = $1", dm_id)

    # Trigger email sequence
    await email_service.trigger_sequence(customer_id, "reddit_lead_nurture")

    return customer_id
```

---

## 💡 Future Enhancements

### Phase 2 (Month 6-9)
- Twitter monitoring (same concept)
- Quora monitoring
- LinkedIn group monitoring
- Auto-generate Reddit posts (not just comments)

### Phase 3 (Month 9-12)
- Image/meme generation for higher engagement
- Video responses (Loom links)
- AMA (Ask Me Anything) sessions
- Reddit ads integration

---

**BUILD THIS MACHINE = INFINITE REDDIT LEADS**

Deploy once. Runs 24/7. Provides genuine value. Generates passive leads forever.

**Status:** 🔵 Spec complete, ready for builder to claim
**Priority:** MEDIUM (Week 4-5)
**ROI:** 300x (10 hours work → $30K/year value)
