# SEO Landing Page Generator - Technical Specification

**Service:** seo-landing-generator
**Type:** Autonomous Machine (infinite scale)
**Priority:** MEDIUM (Week 3-4)
**Build Time:** 14 hours
**Impact:** 1,000+ landing pages, long-tail SEO dominance, massive organic traffic

---

## 🎯 Mission

Programmatically generate 1,000+ SEO-optimized landing pages targeting long-tail keywords. Capture every possible search intent. Become the #1 result for hundreds of niche queries.

---

## 💰 Business Impact

### The Long-Tail Strategy

**Single generic page:** "church coaching" (high competition, rank #50+)
**1,000 specific pages:** Each targets ultra-specific query, easier to rank #1

Examples:
- "church growth coach for rural methodist churches under 100 members"
- "youth ministry consultant for urban baptist churches in texas"
- "worship team leadership training for contemporary christian churches"
- "small group multiplication strategy for presbyterian churches"

### Revenue Impact
- **1,000 pages × 20 visitors/month = 20,000 organic visitors/month**
- **2% conversion = 400 leads/month**
- **10% close rate = 40 customers/month**
- **$2,500 avg = $100,000/month revenue**
- **Annual value: $1.2M**

### Timeline
- **Week 1:** Generate 100 pages, deploy, submit sitemap
- **Month 1:** Generate 500 pages, 500+ organic visitors/month
- **Month 3:** Generate 1,000 pages, 5,000+ organic visitors/month
- **Month 6:** 1,500+ pages, 15,000+ organic visitors/month
- **Month 12:** 2,000+ pages, 50,000+ organic visitors/month

### Strategic Value
- Long-tail keyword monopoly
- Unlimited scalability (can generate 10,000+ pages)
- Zero marginal cost per page
- Evergreen (pages work forever)
- Compounds with content engine

---

## 🏗️ Architecture

### Tech Stack
- **Framework:** Next.js (SSG - Static Site Generation)
- **Template Engine:** React + TypeScript
- **Database:** PostgreSQL (page tracking, keyword research)
- **Keyword Research:** Ahrefs API / SEMrush API
- **LLM:** GPT-4 (for unique content per page)
- **Hosting:** Vercel or Cloudflare Pages (auto-scale)
- **SEO:** Schema.org markup, sitemap.xml auto-generation
- **Monitoring:** Google Search Console API

### System Flow
```
┌──────────────────────────────────────────────────┐
│  SEO Landing Page Generator                      │
├──────────────────────────────────────────────────┤
│                                                  │
│  1. Keyword Research Engine                      │
│     - Scrape long-tail keywords (Ahrefs API)    │
│     - Analyze search volume + competition       │
│     - Prioritize by ROI (volume × relevance)    │
│     - Generate keyword combinations             │
│                                                  │
│  2. Page Template System                         │
│     - Hero section (H1 with keyword)            │
│     - Service description                        │
│     - "Why choose us" section                    │
│     - Provider showcase (matching service)       │
│     - Testimonials (relevant to service)         │
│     - FAQ (keyword variations)                   │
│     - CTA (Get matched button)                   │
│                                                  │
│  3. Content Generator (GPT-4)                    │
│     - Unique content for each page              │
│     - SEO-optimized copy (keyword density)       │
│     - Natural language (not spammy)              │
│     - Schema.org structured data                 │
│                                                  │
│  4. Static Site Generator                        │
│     - Build 1,000 static HTML pages             │
│     - Lightning fast (CDN-served)                │
│     - Perfect SEO (crawlable, indexable)         │
│     - Auto-deploy to Vercel                      │
│                                                  │
│  5. Performance Tracker                          │
│     - Google Search Console integration          │
│     - Track rankings per keyword                 │
│     - Identify winners (top 3 results)           │
│     - Auto-generate more similar pages           │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 📋 Keyword Strategy

### Keyword Formula

**Base Services:**
- Church coaching
- Ministry consulting
- Pastoral coaching
- Worship training
- Youth ministry consulting
- Small group coaching
- Church leadership development
- Nonprofit consulting

**Modifiers (Location):**
- [City] (top 100 US cities)
- [State] (50 states)
- Urban / Rural / Suburban
- Online (remote)

**Modifiers (Denomination):**
- Baptist
- Methodist
- Presbyterian
- Pentecostal
- Non-denominational
- Catholic
- Lutheran
- Anglican
- etc. (20+ denominations)

**Modifiers (Size):**
- Small (under 100)
- Medium (100-500)
- Large (500-2000)
- Megachurch (2000+)

**Modifiers (Specialty):**
- Church planting
- Church revitalization
- Multisite strategy
- Digital ministry
- Online church
- Hybrid church

### Example Combinations

**Formula:** `{service} for {size} {denomination} churches in {location}`

Generated pages:
1. "church-growth-coaching-small-baptist-churches-rural-texas"
2. "worship-training-medium-pentecostal-churches-atlanta"
3. "youth-ministry-consulting-large-nondenominational-churches-online"
4. "pastoral-coaching-church-planters-presbyterian-california"
5. ... (1,000+ more)

### Keyword Research Automation
```python
import httpx
from typing import List, Dict

class KeywordResearcher:
    """Automated keyword research using Ahrefs API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient()

    async def get_long_tail_keywords(self, seed_keyword: str, limit: int = 100) -> List[Dict]:
        """Get long-tail keyword variations"""

        response = await self.client.get(
            "https://api.ahrefs.com/v3/keywords-explorer/phrase-match",
            params={
                "token": self.api_key,
                "phrase": seed_keyword,
                "country": "us",
                "limit": limit,
                "order_by": "volume:desc"
            }
        )

        keywords = response.json()['keywords']

        # Filter for low competition, decent volume
        long_tail = [
            kw for kw in keywords
            if kw['difficulty'] < 30  # Easy to rank
            and kw['volume'] >= 50  # Worth targeting
            and len(kw['keyword'].split()) >= 4  # Long-tail
        ]

        return long_tail

    async def generate_keyword_combinations(self) -> List[str]:
        """Generate all possible keyword combinations"""

        services = ["church coaching", "ministry consulting", "pastoral coaching", "worship training"]
        sizes = ["small", "medium", "large"]
        denominations = ["baptist", "methodist", "presbyterian", "pentecostal", "nondenominational"]
        locations = ["texas", "california", "florida", "new york", "online"]

        combinations = []
        for service in services:
            for size in sizes:
                for denom in denominations:
                    for loc in locations:
                        keyword = f"{service} for {size} {denom} churches in {loc}"
                        slug = keyword.replace(" ", "-").lower()
                        combinations.append({
                            "keyword": keyword,
                            "slug": slug,
                            "service": service,
                            "size": size,
                            "denomination": denom,
                            "location": loc
                        })

        # 4 × 3 × 5 × 5 = 300 combinations
        # Add more modifiers to reach 1,000+

        return combinations
```

---

## 🎨 Page Template

### URL Structure
```
https://fullpotential.com/services/{service-slug}-{location}

Examples:
/services/church-growth-coaching-small-baptist-churches-rural-texas
/services/worship-training-atlanta-georgia
/services/youth-ministry-consulting-online
```

### Page Components (React)

**1. Hero Section**
```tsx
<Hero>
  <h1>{keyword}</h1>
  <p>Connect with expert {service} providers specializing in {niche}</p>
  <Button>Get Matched in 2 Minutes</Button>
  <TrustBadges />
</Hero>

// Example output:
// <h1>Church Growth Coaching for Small Baptist Churches in Rural Texas</h1>
```

**2. Service Description**
```tsx
<ServiceDescription>
  <h2>Professional {service} for {target audience}</h2>
  <p>{GPT-4 generated unique content about this specific service}</p>

  <Benefits>
    <li>Proven strategies for {specific challenge}</li>
    <li>Experience with {denomination} theology and culture</li>
    <li>Understanding of {location} church landscape</li>
    <li>Specialized in {size} church dynamics</li>
  </Benefits>
</ServiceDescription>
```

**3. Provider Showcase**
```tsx
<Providers>
  <h2>Meet Our {service} Experts</h2>

  {/* Query database for providers matching this service */}
  {providers.filter(p => p.specialties.includes(service_type)).map(provider => (
    <ProviderCard
      name={provider.name}
      specialty={provider.specialty}
      experience={provider.years_experience}
      pricing={provider.pricing_range}
    />
  ))}

  <Button>See All Providers & Get Matched</Button>
</Providers>
```

**4. Testimonials**
```tsx
<Testimonials>
  <h2>Success Stories from {denomination} Churches in {location}</h2>

  {/* Query testimonials matching filters */}
  {testimonials.filter(match_criteria).map(t => (
    <Testimonial
      quote={t.quote}
      author={t.author}
      church={t.church_name}
      result={t.result}
    />
  ))}
</Testimonials>
```

**5. FAQ Section (Schema.org)**
```tsx
<FAQ schema="FAQPage">
  <Question>How much does {service} cost in {location}?</Question>
  <Answer>{GPT-4 generated answer with pricing info}</Answer>

  <Question>What makes {denomination} church coaching different?</Question>
  <Answer>{GPT-4 generated answer about denomination-specific needs}</Answer>

  <Question>How long does {service} typically take for {size} churches?</Question>
  <Answer>{GPT-4 generated answer}</Answer>

  <Question>Do you have {service} providers who work remotely?</Question>
  <Answer>Yes, many of our providers offer online {service}...</Answer>
</FAQ>
```

**6. Call to Action**
```tsx
<CTA>
  <h2>Find Your Perfect {service} Provider</h2>
  <p>Tell us about your church and get matched with vetted experts in minutes.</p>
  <Button large>Get Matched Now</Button>
  <Guarantee>Free matching · 24-hour response · Vetted providers</Guarantee>
</CTA>
```

---

## 🤖 Content Generation

### GPT-4 Template for Unique Content
```python
PAGE_CONTENT_PROMPT = """
Generate SEO-optimized, unique content for a landing page targeting this keyword:

Keyword: {keyword}
Service: {service}
Target Audience: {size} {denomination} churches in {location}

Write:
1. Service description (150 words)
   - What the service is
   - Why it's valuable for this specific audience
   - Key benefits
   - Common challenges it solves

2. "Why Choose Us" section (100 words)
   - Expertise in {denomination} theology/culture
   - Understanding of {location} church landscape
   - Experience with {size} church dynamics
   - Proven results

3. FAQ answers (3 questions × 75 words each)
   - How much does {service} cost?
   - What makes {denomination} coaching different?
   - How long does {service} take for {size} churches?

Requirements:
- Natural language (not keyword-stuffed)
- Use "{keyword}" exactly 3-4 times
- Use variations and related terms
- Professional, trustworthy tone
- Specific to target audience (not generic)

Output JSON:
{
  "service_description": "...",
  "why_choose_us": "...",
  "faq": [
    {"question": "...", "answer": "..."},
    ...
  ]
}
"""
```

### Content Uniqueness Check
```python
from difflib import SequenceMatcher

async def ensure_uniqueness(new_content: str, existing_pages: List[str]) -> bool:
    """Ensure content is >85% unique compared to existing pages"""

    for existing in existing_pages:
        similarity = SequenceMatcher(None, new_content, existing).ratio()
        if similarity > 0.15:  # More than 15% similar
            return False  # Reject, too similar

    return True  # Unique enough
```

---

## 🏗️ Static Site Generation

### Next.js Implementation

**pages/services/[slug].tsx**
```tsx
import { GetStaticPaths, GetStaticProps } from 'next';

interface ServicePageProps {
  keyword: string;
  service: string;
  size: string;
  denomination: string;
  location: string;
  content: {
    service_description: string;
    why_choose_us: string;
    faq: Array<{question: string; answer: string}>;
  };
  providers: Provider[];
  testimonials: Testimonial[];
}

export default function ServicePage(props: ServicePageProps) {
  return (
    <>
      <Head>
        <title>{props.keyword} | Full Potential AI</title>
        <meta name="description" content={props.content.service_description.substring(0, 155)} />
        <link rel="canonical" href={`https://fullpotential.com/services/${props.slug}`} />
      </Head>

      <Hero keyword={props.keyword} service={props.service} />
      <ServiceDescription content={props.content.service_description} benefits={...} />
      <Providers providers={props.providers} />
      <Testimonials testimonials={props.testimonials} />
      <FAQ faqs={props.content.faq} />
      <CTA service={props.service} />
    </>
  );
}

// Generate static paths for all 1,000+ keywords
export const getStaticPaths: GetStaticPaths = async () => {
  // Fetch all keyword combinations from database
  const keywords = await db.query("SELECT slug FROM landing_pages WHERE status = 'published'");

  const paths = keywords.map(kw => ({
    params: { slug: kw.slug }
  }));

  return {
    paths,
    fallback: false  // 404 for non-existent pages
  };
};

// Generate page props at build time
export const getStaticProps: GetStaticProps = async ({ params }) => {
  const page = await db.query("SELECT * FROM landing_pages WHERE slug = $1", [params.slug]);
  const providers = await db.query("SELECT * FROM providers WHERE service_type = $1 LIMIT 3", [page.service]);
  const testimonials = await db.query("SELECT * FROM testimonials WHERE service_type = $1 LIMIT 3", [page.service]);

  return {
    props: {
      ...page,
      providers,
      testimonials
    },
    revalidate: 86400  // Re-generate daily
  };
};
```

### Build Process
```bash
# Generate all pages
npm run generate-pages  # Runs Python script to create landing_pages in DB

# Build static site
next build  # Generates 1,000+ static HTML files

# Deploy to Vercel
vercel deploy --prod
```

---

## 📊 Database Schema

```sql
CREATE TABLE landing_pages (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,

    -- Keyword components
    service VARCHAR(100),
    size VARCHAR(50),
    denomination VARCHAR(50),
    location VARCHAR(100),

    -- Generated content
    service_description TEXT,
    why_choose_us TEXT,
    faq JSONB,

    -- SEO
    meta_title VARCHAR(70),
    meta_description VARCHAR(160),
    h1 VARCHAR(100),

    -- Tracking
    search_volume INTEGER,
    keyword_difficulty INTEGER,
    estimated_traffic INTEGER,

    -- Performance
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    avg_position DECIMAL(5,2),
    conversions INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(20) DEFAULT 'draft',  -- draft | published | archived
    generated_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,
    last_updated TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_landing_pages_slug ON landing_pages(slug);
CREATE INDEX idx_landing_pages_service ON landing_pages(service);
CREATE INDEX idx_landing_pages_location ON landing_pages(location);
CREATE INDEX idx_landing_pages_status ON landing_pages(status);
```

---

## 📈 Performance Tracking

### Google Search Console Integration
```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

class SEOPerformanceTracker:
    """Track landing page performance via Search Console"""

    def __init__(self, credentials_path: str):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        self.service = build('searchconsole', 'v1', credentials=credentials)

    async def get_page_performance(self, url: str, days: int = 30):
        """Get impressions, clicks, position for specific page"""

        request = {
            'startDate': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
            'endDate': datetime.now().strftime('%Y-%m-%d'),
            'dimensions': ['page'],
            'dimensionFilterGroups': [{
                'filters': [{
                    'dimension': 'page',
                    'expression': url
                }]
            }]
        }

        response = self.service.searchanalytics().query(
            siteUrl='https://fullpotential.com',
            body=request
        ).execute()

        if 'rows' in response:
            row = response['rows'][0]
            return {
                'impressions': row['impressions'],
                'clicks': row['clicks'],
                'ctr': row['ctr'],
                'position': row['position']
            }

        return None

    async def identify_winners(self, min_position: float = 10.0):
        """Find pages ranking in top 10"""

        pages = await db.fetch_all("SELECT * FROM landing_pages WHERE status = 'published'")

        winners = []
        for page in pages:
            perf = await self.get_page_performance(f"https://fullpotential.com/services/{page['slug']}")

            if perf and perf['position'] <= min_position:
                winners.append({
                    "page": page,
                    "performance": perf,
                    "action": "create_more_similar_pages"
                })

        return winners

    async def identify_losers(self, max_position: float = 50.0, min_age_days: int = 90):
        """Find old pages ranking poorly"""

        pages = await db.fetch_all("""
            SELECT * FROM landing_pages
            WHERE status = 'published'
            AND published_at < NOW() - INTERVAL '{} days'
        """.format(min_age_days))

        losers = []
        for page in pages:
            perf = await self.get_page_performance(f"https://fullpotential.com/services/{page['slug']}")

            if perf and perf['position'] > max_position:
                losers.append({
                    "page": page,
                    "performance": perf,
                    "action": "archive_or_rewrite"
                })

        return losers
```

### Auto-Optimization Loop
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', day=1, hour=2)  # Monthly on 1st at 2am
async def optimize_landing_pages():
    """Automatically optimize landing page portfolio"""

    tracker = SEOPerformanceTracker(credentials_path="gsc_credentials.json")

    # 1. Find winners (top 10 rankings)
    winners = await tracker.identify_winners()

    for item in winners:
        # Generate 5 more pages similar to this winner
        similar_keywords = await keyword_researcher.get_similar_keywords(item['page']['keyword'])

        for keyword in similar_keywords[:5]:
            await generate_landing_page(keyword)

        logger.info(f"🏆 Winner: {item['page']['keyword']} (pos {item['performance']['position']}) - Generated 5 similar")

    # 2. Find losers (position >50 after 90 days)
    losers = await tracker.identify_losers()

    for item in losers:
        # Archive poorly performing pages
        await db.execute("UPDATE landing_pages SET status = 'archived' WHERE id = $1", item['page']['id'])
        logger.info(f"📦 Archived: {item['page']['keyword']} (pos {item['performance']['position']})")

    # 3. Generate new pages to replace archived ones
    new_keywords = await keyword_researcher.get_fresh_keywords(limit=len(losers))
    for keyword in new_keywords:
        await generate_landing_page(keyword)

    logger.info(f"♻️  Optimization complete: +{len(winners)*5} winners, -{len(losers)} losers, +{len(losers)} new")
```

---

## 🚀 Deployment

### Vercel Deployment
```bash
# Install Vercel CLI
npm i -g vercel

# Configure project
vercel link

# Set environment variables
vercel env add DATABASE_URL
vercel env add OPENAI_API_KEY

# Deploy to production
vercel --prod
```

### Automated Build Pipeline
```yaml
# .github/workflows/build-pages.yml
name: Generate and Deploy Landing Pages

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2am
  workflow_dispatch:  # Manual trigger

jobs:
  generate-pages:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Generate new landing pages
        run: |
          python scripts/generate_landing_pages.py --batch-size 50

      - name: Build Next.js site
        run: |
          npm install
          npm run build

      - name: Deploy to Vercel
        run: |
          vercel deploy --prod --token ${{ secrets.VERCEL_TOKEN }}

      - name: Submit sitemap to Google
        run: |
          curl "https://www.google.com/ping?sitemap=https://fullpotential.com/sitemap.xml"
```

---

## 🗺️ Sitemap Generation

### Dynamic Sitemap
```typescript
// pages/sitemap.xml.tsx
import { GetServerSideProps } from 'next';

export const getServerSideProps: GetServerSideProps = async ({ res }) => {
  const pages = await db.query("SELECT slug, last_updated FROM landing_pages WHERE status = 'published'");

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      ${pages.map(page => `
        <url>
          <loc>https://fullpotential.com/services/${page.slug}</loc>
          <lastmod>${page.last_updated.toISOString()}</lastmod>
          <changefreq>weekly</changefreq>
          <priority>0.8</priority>
        </url>
      `).join('')}
    </urlset>
  `;

  res.setHeader('Content-Type', 'text/xml');
  res.write(sitemap);
  res.end();

  return { props: {} };
};

export default function Sitemap() {
  return null;
}
```

---

## ✅ Success Criteria

### Functional Requirements
- ✅ Generate 1,000+ unique landing pages
- ✅ <85% content similarity across pages
- ✅ All pages have schema.org markup
- ✅ Sitemap auto-updates with new pages
- ✅ Integrate with I MATCH API (Get Matched button)
- ✅ Mobile-responsive design
- ✅ <2 second page load time

### SEO Requirements
- ✅ Unique title, meta description per page
- ✅ H1 contains exact target keyword
- ✅ 3-5 keyword mentions per page (natural)
- ✅ Internal linking between related pages
- ✅ Schema.org FAQPage markup
- ✅ Canonical URLs properly set
- ✅ Google Search Console tracking

### Performance Requirements
- ✅ 100/100 Lighthouse SEO score
- ✅ 90+ Lighthouse Performance score
- ✅ All pages indexed within 7 days
- ✅ 50% of pages rank top 50 within 90 days
- ✅ 20% of pages rank top 10 within 180 days

### Business Requirements
- ✅ 5,000+ organic visitors/month by Month 3
- ✅ 15,000+ organic visitors/month by Month 6
- ✅ 50,000+ organic visitors/month by Month 12
- ✅ 2% visitor → lead conversion
- ✅ $100K+ monthly revenue by Month 12

---

## 📊 Expected Outcomes

### Month 1
- **Pages generated:** 500
- **Pages indexed:** 300
- **Organic traffic:** 500 visitors
- **Leads:** 10
- **Revenue:** $1,000-2,000

### Month 3
- **Pages generated:** 1,000
- **Pages indexed:** 800
- **Organic traffic:** 5,000 visitors
- **Leads:** 100
- **Revenue:** $10,000-20,000

### Month 6
- **Pages generated:** 1,500
- **Pages indexed:** 1,200
- **Organic traffic:** 15,000 visitors
- **Leads:** 300
- **Revenue:** $30,000-60,000

### Month 12
- **Pages generated:** 2,000
- **Pages indexed:** 1,800
- **Organic traffic:** 50,000 visitors
- **Leads:** 1,000
- **Revenue:** $100,000-200,000

### Infinite Horizon
- Can generate 10,000+ pages (unlimited)
- Each page works forever (evergreen)
- Compounds with content engine
- Domain authority increases exponentially
- **INFINITE TRAFFIC**

---

## 🔗 Integration Points

### With I MATCH System
```tsx
<GetMatchedButton onClick={() => {
  // Pre-fill intake form with page context
  window.location.href = `/get-matched?service=${service}&location=${location}`;
}}>
  Get Matched with a {service} Expert
</GetMatchedButton>
```

### With Content Engine
```tsx
<RelatedContent>
  <h2>Learn More About {service}</h2>
  {/* Query blog articles matching service type */}
  {articles.map(article => <ArticleCard {...article} />)}
</RelatedContent>
```

### With Email Automation
```python
# When user submits from landing page, tag them
async def track_landing_page_conversion(customer_id: int, landing_page_slug: str):
    await db.execute("""
        UPDATE customers
        SET acquisition_source = 'landing_page',
            acquisition_details = $1
        WHERE id = $2
    """, landing_page_slug, customer_id)

    # Trigger specialized email sequence
    await email_service.trigger_sequence(customer_id, "landing_page_followup")
```

---

## 💡 Future Enhancements

### Phase 2 (Month 6-9)
- Multi-language pages (Spanish, Portuguese)
- Video testimonials embedded
- Live chat integration
- A/B testing different CTAs
- Dynamic pricing display

### Phase 3 (Month 9-12)
- Programmatic PPC landing pages
- City-specific pages (1,000+ cities)
- Competitor comparison pages
- Industry-specific verticals (nonprofits, schools)

---

**BUILD THIS MACHINE = 1,000+ PAGES WORKING 24/7**

Deploy once. Generates infinite pages. Captures all long-tail traffic. Zero maintenance.

**Status:** 🔵 Spec complete, ready for builder to claim
**Priority:** MEDIUM (Week 3-4)
**ROI:** 10,000x (1,000 pages × 20 visitors/month × $5 value = $100K/month for 14 hours work)
