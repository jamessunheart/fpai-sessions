# Content Generation Engine - Technical Specification

**Service:** content-generation-engine
**Type:** Autonomous Machine (runs forever)
**Priority:** HIGH (Week 2-3)
**Build Time:** 12 hours
**Impact:** Infinite evergreen content, SEO flywheel, zero manual writing

---

## 🎯 Mission

Generate unlimited SEO-optimized blog content automatically from customer data, success stories, and industry insights. Publish forever without human intervention.

---

## 💰 Business Impact

### Revenue Impact
- **Organic traffic growth:** 50-100 visitors/month per article
- **SEO compound effect:** Each article works forever
- **Lead generation:** 2-5% visitor → customer conversion
- **Expected value:** $30K/year by month 12

### Metrics
- **Week 1:** 3 articles published, indexed by Google
- **Month 1:** 12 articles published, 200+ organic visitors/month
- **Month 3:** 36 articles published, 1,500+ organic visitors/month
- **Month 12:** 144 articles published, 10,000+ organic visitors/month

### Strategic Value
- Evergreen content library (works forever)
- SEO domain authority improvement
- Zero content creation cost
- Compounds exponentially

---

## 🏗️ Architecture

### Tech Stack
- **Framework:** FastAPI (async)
- **LLM:** OpenAI GPT-4 (for content generation)
- **Database:** PostgreSQL (article tracking, customer data)
- **Scheduling:** APScheduler (cron-based publishing)
- **CMS Integration:** WordPress REST API or Ghost API
- **SEO:** sitemap.xml auto-update, meta tags
- **Monitoring:** Prometheus + Sentry

### Components
```
┌─────────────────────────────────────────────┐
│  Content Generation Engine                  │
├─────────────────────────────────────────────┤
│                                             │
│  1. Content Strategist                      │
│     - Topic research (trending keywords)    │
│     - Customer data mining                  │
│     - Success story extraction              │
│     - Content calendar generation           │
│                                             │
│  2. AI Writer                               │
│     - GPT-4 article generation              │
│     - SEO optimization (keywords, meta)     │
│     - Formatting (H1-H4, lists, bold)       │
│     - Image suggestions                     │
│                                             │
│  3. Publishing System                       │
│     - WordPress/Ghost API integration       │
│     - Auto-scheduling (3x/week)             │
│     - Category/tag assignment               │
│     - Sitemap update                        │
│                                             │
│  4. Performance Tracker                     │
│     - Google Analytics integration          │
│     - Traffic monitoring per article        │
│     - Keyword ranking tracking              │
│     - Auto-optimization (rewrite low perf)  │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📋 API Endpoints

### 1. Content Generation
```http
POST /content/generate
Content-Type: application/json

{
  "topic_source": "customer_success | trending_keyword | manual",
  "customer_id": 123,  # optional, for success stories
  "keyword": "church leadership coaching",  # optional
  "tone": "professional | conversational | inspiring",
  "length": "short | medium | long"  # 500 | 1000 | 2000 words
}

Response:
{
  "article_id": "art_abc123",
  "title": "How Small Churches Doubled Attendance in 90 Days",
  "slug": "how-small-churches-doubled-attendance-90-days",
  "content": "<full HTML content>",
  "seo": {
    "meta_description": "...",
    "keywords": ["church growth", "attendance", ...],
    "estimated_reading_time": "5 min"
  },
  "status": "draft",
  "generated_at": "2025-11-15T22:00:00Z"
}
```

### 2. Publish Article
```http
POST /content/publish/{article_id}

Response:
{
  "published_url": "https://fullpotential.com/blog/how-small-churches-doubled-attendance-90-days",
  "published_at": "2025-11-15T22:00:00Z",
  "status": "published"
}
```

### 3. Content Calendar
```http
GET /content/calendar?weeks=4

Response:
{
  "calendar": [
    {
      "date": "2025-11-18",
      "topic": "Church leadership coaching success story",
      "status": "scheduled",
      "article_id": "art_abc123"
    },
    {
      "date": "2025-11-20",
      "topic": "5 ways AI improves church operations",
      "status": "draft"
    }
  ],
  "total_scheduled": 12,
  "next_publish_date": "2025-11-18"
}
```

### 4. Performance Dashboard
```http
GET /content/performance

Response:
{
  "total_articles": 36,
  "total_views": 15000,
  "avg_time_on_page": "3:45",
  "top_articles": [
    {
      "title": "How Small Churches Doubled Attendance",
      "views": 2500,
      "conversion_rate": 0.035
    }
  ],
  "seo_metrics": {
    "avg_position": 15.3,
    "keywords_ranking": 47,
    "domain_authority": 32
  }
}
```

---

## 🧠 Content Strategy

### Topic Sources

**1. Customer Success Stories (40% of content)**
```sql
-- Mine customer data for success stories
SELECT
  c.name,
  c.service_type,
  m.provider_name,
  c.created_at
FROM customers c
JOIN matches m ON c.id = m.customer_id
WHERE m.status = 'converted'
ORDER BY c.created_at DESC
LIMIT 10;

-- Generate article:
-- "How [Customer] Achieved [Result] with [Provider]"
```

**2. Trending Keywords (30% of content)**
```python
# Use Google Trends API or Ahrefs API
keywords = [
    "church growth strategies 2025",
    "small church leadership",
    "church digital transformation",
    "pastoral coaching",
    "church online presence"
]

# Generate article for each trending keyword
```

**3. Educational Content (20% of content)**
```
Topics:
- "Complete guide to church leadership coaching"
- "10 mistakes churches make when hiring consultants"
- "How to choose the right ministry coach"
- "Church growth: DIY vs professional help"
```

**4. Industry Insights (10% of content)**
```
Topics:
- "State of church leadership in 2025"
- "AI in ministry: opportunities and challenges"
- "The future of church consulting"
```

### Content Templates

**Template 1: Success Story**
```markdown
# How [Customer Name] [Achieved Result] in [Timeframe]

**Challenge:** [Customer's initial problem]

**Solution:** [How our provider helped]

**Results:**
- [Metric 1]
- [Metric 2]
- [Metric 3]

**Takeaways:** [3-5 lessons]

**[CTA: Get matched with a provider like this]**
```

**Template 2: Educational Guide**
```markdown
# [Number] [Topic] Every [Audience] Should Know

**Introduction:** [Hook + problem statement]

**[Point 1]**
[Explanation + example]

**[Point 2]**
[Explanation + example]

...

**Conclusion:** [Summary + CTA]
```

**Template 3: Comparison/Review**
```markdown
# [Option A] vs [Option B]: Which is Right for Your Church?

**Overview:** [Comparison introduction]

**[Option A]**
Pros: ...
Cons: ...
Best for: ...

**[Option B]**
Pros: ...
Cons: ...
Best for: ...

**Conclusion:** [Recommendation + CTA]
```

---

## 🤖 AI Writer Implementation

### GPT-4 Prompt Template
```python
CONTENT_GENERATION_PROMPT = """
You are a professional content writer for Full Potential AI, a platform that matches churches and ministries with expert coaches and consultants.

Write a {length}-word blog article on the following topic:
Topic: {topic}
Keywords to include: {keywords}
Tone: {tone}
Customer data (if applicable): {customer_data}

Requirements:
1. SEO-optimized (use keywords naturally 3-5 times)
2. Engaging, valuable content for church leaders
3. Include actionable takeaways
4. End with a clear call-to-action to use Full Potential AI
5. Use proper HTML formatting (H1, H2, H3, <p>, <ul>, <strong>)
6. Meta description (155 characters max)

Output format:
{
  "title": "...",
  "meta_description": "...",
  "content": "<html content>",
  "keywords": ["keyword1", "keyword2", ...]
}
"""
```

### Content Quality Checks
```python
async def validate_content(article: str) -> bool:
    """Validate generated content meets quality standards"""
    checks = {
        "min_word_count": len(article.split()) >= 500,
        "has_headings": "<h2>" in article and "<h3>" in article,
        "has_cta": "get matched" in article.lower() or "find a coach" in article.lower(),
        "keyword_density": 0.01 <= calculate_keyword_density(article) <= 0.03,
        "readability": flesch_reading_ease(article) >= 60,  # Grade 8-9 level
        "no_duplicates": not is_duplicate(article)
    }

    return all(checks.values())
```

---

## 📅 Publishing Schedule

### Automated Cron Jobs
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Generate 3 articles per week (Mon, Wed, Fri at 6am)
@scheduler.scheduled_job('cron', day_of_week='mon,wed,fri', hour=6)
async def generate_and_publish():
    """Generate article and publish automatically"""

    # 1. Determine topic (rotate through sources)
    topic = await strategist.get_next_topic()

    # 2. Generate article
    article = await writer.generate_article(topic)

    # 3. Quality check
    if await validate_content(article['content']):
        # 4. Publish to WordPress
        published_url = await publisher.publish(article)

        # 5. Track metrics
        await tracker.log_publication(article['id'], published_url)

        logger.info(f"✅ Published: {published_url}")
    else:
        logger.warning(f"❌ Article failed quality check: {article['title']}")
        # Regenerate with feedback
        await writer.regenerate_article(topic, feedback="Improve quality")
```

---

## 🔌 WordPress Integration

### Publishing via REST API
```python
import httpx

class WordPressPublisher:
    """Publish articles to WordPress via REST API"""

    def __init__(self, site_url: str, username: str, app_password: str):
        self.site_url = site_url
        self.auth = (username, app_password)
        self.client = httpx.AsyncClient()

    async def publish_article(self, article: Dict) -> str:
        """Publish article to WordPress"""

        # Create post
        response = await self.client.post(
            f"{self.site_url}/wp-json/wp/v2/posts",
            auth=self.auth,
            json={
                "title": article['title'],
                "content": article['content'],
                "slug": article['slug'],
                "status": "publish",  # or "draft" for review
                "categories": [self.get_category_id("Blog")],
                "tags": [self.get_tag_id(tag) for tag in article['seo']['keywords']],
                "meta": {
                    "description": article['seo']['meta_description']
                }
            }
        )

        if response.status_code == 201:
            post_data = response.json()
            return post_data['link']
        else:
            raise Exception(f"Failed to publish: {response.text}")

    async def update_article(self, article_id: str, content: str):
        """Update existing article (for optimization)"""
        await self.client.post(
            f"{self.site_url}/wp-json/wp/v2/posts/{article_id}",
            auth=self.auth,
            json={"content": content}
        )
```

---

## 📊 Performance Tracking

### Google Analytics Integration
```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest

class PerformanceTracker:
    """Track article performance via Google Analytics"""

    async def get_article_metrics(self, article_slug: str, days: int = 30):
        """Get pageviews, avg time, bounce rate for article"""

        client = BetaAnalyticsDataClient()

        request = RunReportRequest(
            property=f"properties/{GA_PROPERTY_ID}",
            dimensions=[{"name": "pagePath"}],
            metrics=[
                {"name": "screenPageViews"},
                {"name": "averageSessionDuration"},
                {"name": "bounceRate"}
            ],
            dimension_filter={
                "filter": {
                    "field_name": "pagePath",
                    "string_filter": {"value": f"/blog/{article_slug}"}
                }
            },
            date_ranges=[{"start_date": f"{days}daysAgo", "end_date": "today"}]
        )

        response = client.run_report(request)

        return {
            "views": int(response.rows[0].metric_values[0].value),
            "avg_time": float(response.rows[0].metric_values[1].value),
            "bounce_rate": float(response.rows[0].metric_values[2].value)
        }

    async def identify_underperformers(self, threshold_views: int = 50):
        """Find articles with low performance for re-optimization"""

        articles = await db.fetch_all("SELECT * FROM articles WHERE published_at < NOW() - INTERVAL '30 days'")

        underperformers = []
        for article in articles:
            metrics = await self.get_article_metrics(article['slug'])
            if metrics['views'] < threshold_views:
                underperformers.append({
                    "article": article,
                    "metrics": metrics,
                    "action": "rewrite_with_better_seo"
                })

        return underperformers
```

### Auto-Optimization Loop
```python
@scheduler.scheduled_job('cron', day=1, hour=3)  # Monthly on 1st at 3am
async def optimize_underperforming_articles():
    """Automatically improve low-performing articles"""

    underperformers = await tracker.identify_underperformers()

    for item in underperformers:
        article = item['article']
        metrics = item['metrics']

        # Re-generate with SEO improvement instructions
        improved_article = await writer.regenerate_article(
            topic=article['topic'],
            feedback=f"Original got only {metrics['views']} views. Improve SEO and engagement."
        )

        # Update on WordPress
        await publisher.update_article(article['wordpress_id'], improved_article['content'])

        logger.info(f"♻️  Optimized article: {article['title']}")
```

---

## 🗄️ Database Schema

```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    meta_description VARCHAR(160),
    keywords TEXT[],

    -- Source
    topic_source VARCHAR(50),  -- customer_success | trending_keyword | educational | insights
    customer_id INTEGER REFERENCES customers(id),  -- if success story

    -- Publishing
    status VARCHAR(20) DEFAULT 'draft',  -- draft | scheduled | published
    wordpress_id INTEGER,
    published_url TEXT,
    published_at TIMESTAMP,

    -- Performance
    views INTEGER DEFAULT 0,
    avg_time_seconds INTEGER DEFAULT 0,
    bounce_rate DECIMAL(5,2),
    conversion_rate DECIMAL(5,4),

    -- Metadata
    word_count INTEGER,
    reading_time_minutes INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_published_at ON articles(published_at);
CREATE INDEX idx_articles_topic_source ON articles(topic_source);
```

---

## 🚀 Deployment

### Docker Compose
```yaml
version: '3.8'

services:
  content-engine:
    build: .
    ports:
      - "8700:8700"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/fpai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - WORDPRESS_URL=https://fullpotential.com
      - WORDPRESS_USERNAME=${WP_USERNAME}
      - WORDPRESS_APP_PASSWORD=${WP_APP_PASSWORD}
      - GOOGLE_ANALYTICS_PROPERTY_ID=${GA_PROPERTY_ID}
      - SENTRY_DSN=${SENTRY_DSN}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=fpai
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

### Systemd Service
```ini
[Unit]
Description=Content Generation Engine
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/fpai/content-generation-engine
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## ✅ Success Criteria

### Functional Requirements
- ✅ Generate 500-2000 word SEO-optimized articles
- ✅ Publish to WordPress automatically 3x/week
- ✅ Track performance via Google Analytics
- ✅ Auto-optimize underperforming content
- ✅ Support multiple content types (success stories, guides, comparisons)
- ✅ Zero human intervention required

### Performance Requirements
- ✅ Generate article in <60 seconds
- ✅ Quality check pass rate >90%
- ✅ Publishing success rate >99%
- ✅ Content uniqueness >95% (no plagiarism)
- ✅ SEO score >70/100 (Yoast or similar)

### Business Requirements
- ✅ 200+ organic visitors/month by Month 1
- ✅ 1,500+ organic visitors/month by Month 3
- ✅ 10,000+ organic visitors/month by Month 12
- ✅ 2-5% visitor → customer conversion
- ✅ $30K+ annual value from organic traffic

---

## 🧪 Testing Strategy

### Unit Tests
```python
async def test_article_generation():
    """Test GPT-4 article generation"""
    article = await writer.generate_article({
        "topic": "church leadership coaching",
        "tone": "professional",
        "length": "medium"
    })

    assert len(article['content'].split()) >= 900
    assert article['meta_description']
    assert len(article['keywords']) >= 3

async def test_content_quality():
    """Test quality validation"""
    article = await writer.generate_article({"topic": "test"})
    is_valid = await validate_content(article['content'])
    assert is_valid is True

async def test_wordpress_publishing():
    """Test WordPress API integration"""
    url = await publisher.publish_article({
        "title": "Test Article",
        "content": "<p>Test content</p>",
        "slug": "test-article-" + str(uuid.uuid4())
    })
    assert url.startswith("https://fullpotential.com/blog/")
```

### Integration Tests
```python
async def test_end_to_end_publishing():
    """Test full flow: generate → validate → publish → track"""

    # Generate
    topic = {"topic": "church growth strategies", "tone": "professional"}
    article = await writer.generate_article(topic)

    # Validate
    assert await validate_content(article['content'])

    # Publish
    url = await publisher.publish_article(article)
    assert url

    # Track
    await asyncio.sleep(5)  # Wait for GA to register
    metrics = await tracker.get_article_metrics(article['slug'], days=1)
    assert metrics['views'] >= 0  # At least tracking works
```

---

## 📈 Expected Growth Trajectory

### Month 1
- **Articles published:** 12
- **Organic traffic:** 200 visitors
- **Leads generated:** 4-10
- **Revenue impact:** $500-1,000

### Month 3
- **Articles published:** 36
- **Organic traffic:** 1,500 visitors
- **Leads generated:** 30-75
- **Revenue impact:** $5,000-10,000

### Month 6
- **Articles published:** 72
- **Organic traffic:** 5,000 visitors
- **Leads generated:** 100-250
- **Revenue impact:** $15,000-25,000

### Month 12
- **Articles published:** 144
- **Organic traffic:** 10,000 visitors
- **Leads generated:** 200-500
- **Revenue impact:** $30,000-50,000

### Infinite Horizon
- Articles continue working forever (evergreen)
- SEO authority compounds exponentially
- Each new article adds to domain value
- Zero marginal cost per article
- **INFINITE ROI**

---

## 🔗 Integration Points

### With I MATCH System
```python
# Mine customer success stories
async def get_success_stories():
    """Get customers who converted for success story articles"""
    return await db.fetch_all("""
        SELECT c.*, m.provider_name, m.service_type
        FROM customers c
        JOIN matches m ON c.id = m.customer_id
        WHERE m.status = 'converted'
        AND c.created_at > NOW() - INTERVAL '30 days'
        ORDER BY c.created_at DESC
    """)
```

### With Email Automation
```python
# Send new article to existing customers
async def notify_customers_of_new_content(article_url: str):
    """Email customers when relevant article published"""
    customers = await db.fetch_all("SELECT email FROM customers WHERE subscribed = true")

    for customer in customers:
        await email_service.send_email(
            to=customer['email'],
            subject=f"New resource: {article['title']}",
            template="new_blog_post",
            data={"article_url": article_url}
        )
```

---

## 💡 Future Enhancements

### Phase 2 (Month 3-6)
- Video content generation (YouTube shorts from articles)
- Podcast episode generation (text-to-speech)
- Social media snippet auto-generation
- Guest post distribution to other sites

### Phase 3 (Month 6-12)
- Multi-language support (Spanish, Portuguese)
- Personalized content recommendations
- Interactive content (quizzes, calculators)
- Community-contributed content curation

---

**BUILD THIS MACHINE = INFINITE CONTENT FOREVER**

Deploy once. Runs forever. Compounds exponentially. Zero maintenance.

**Status:** 🔵 Spec complete, ready for builder to claim
**Priority:** HIGH (Week 2-3)
**ROI:** INFINITE (content works forever)
