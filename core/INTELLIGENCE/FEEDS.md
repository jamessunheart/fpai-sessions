# Data Intelligence Engine - Feed Sources

**Last Updated:** 2025-12-03
**Status:** Active
**Engine Version:** 1.0

---

## Overview

The Data Intelligence Engine aggregates data from external sources to feed both AI decision-making and human consciousness. This document tracks all configured data sources.

---

## Active Sources (Free, No Friction)

### 1. Hacker News API
- **URL:** `https://hacker-news.firebaseio.com/v0/`
- **Type:** Tech/AI News
- **Frequency:** Every 30 minutes
- **Auth:** None required
- **Rate Limit:** ~30 req/min
- **Categories:** `tech`, `ai`
- **Relevance:** High for AI, startups, open source

### 2. arXiv API
- **URL:** `https://export.arxiv.org/api/query`
- **Type:** Research Papers
- **Frequency:** Every 6 hours
- **Auth:** None required
- **Rate Limit:** 1 req/3 sec
- **Categories Monitored:**
  - `cs.AI` - Artificial Intelligence
  - `cs.LG` - Machine Learning
  - `cs.CL` - Computation and Language (NLP)
  - `cs.NE` - Neural and Evolutionary Computing
  - `q-bio.NC` - Neurons and Cognition
- **Relevance:** High for AI research, consciousness studies

### 3. RSS Feeds
- **Type:** Curated Blogs/Newsletters
- **Frequency:** Every 1 hour
- **Auth:** None required

**Configured Feeds:**

| Feed | URL | Category |
|------|-----|----------|
| OpenAI Blog | `https://openai.com/blog/rss/` | AI |
| Anthropic | `https://www.anthropic.com/feed.xml` | AI |
| Google AI Blog | `https://blog.google/technology/ai/rss/` | AI |
| TechCrunch | `https://techcrunch.com/feed/` | Tech |
| Mindful | `https://www.mindful.org/feed/` | Consciousness |

---

## Relevance Scoring

Items are scored 0-1 based on keyword matching:

### High Relevance Keywords (0.7-0.95)
- AI/ML: `ai`, `artificial intelligence`, `llm`, `gpt`, `claude`, `autonomous`, `agent`
- Consciousness: `consciousness`, `mindfulness`, `meditation`, `wellness`, `personal development`

### Medium Relevance Keywords (0.5-0.7)
- Tech: `startup`, `open source`, `saas`, `neural`, `transformer`
- Markets: `crypto`, `bitcoin`, `trading`, `defi`

### Low/Negative Keywords
- Filtered out: `politics`, `celebrity`, `sports`, `gossip`

---

## API Endpoints

### Nerve Center (Port 8120)

```
GET  /api/intelligence/feed       - Get curated feed items
GET  /api/intelligence/digest     - Get daily summary
GET  /api/intelligence/stats      - Get feed statistics
GET  /api/intelligence/trending   - Get trending topics
POST /api/intelligence/ingest     - Add manual item
POST /api/intelligence/refresh    - Trigger immediate fetch
```

---

## Adding New Sources

### To add a new RSS feed:
1. Edit `/SERVICES/ai-brain/app/fetchers.py`
2. Add to `RSSFetcher.DEFAULT_FEEDS`:
```python
{
    "url": "https://example.com/feed/",
    "name": "Example Feed",
    "category": Category.TECH,  # or AI, MARKETS, CONSCIOUSNESS
}
```
3. Restart AI Brain service

### To add a new API source:
1. Create new fetcher class in `fetchers.py`
2. Add to `IntelligenceFetcher.fetch_all()` method
3. Update this document

---

## Planned Sources (Requires Setup)

### Phase 2 (May require API keys)
| Source | Type | Status | Notes |
|--------|------|--------|-------|
| Twitter/X API | Social | Pending | Needs API key |
| Reddit API | Social | Pending | Needs OAuth |
| CryptoPanic | News | Pending | Free tier available |

### Phase 3 (Paid or complex)
| Source | Type | Status | Notes |
|--------|------|--------|-------|
| Bloomberg | Finance | Future | Paid API |
| Google Scholar | Research | Future | Scraping required |
| Podcast transcripts | Audio | Future | Whisper needed |

---

## Monitoring

### Health Checks
- Nerve Center: `GET http://localhost:8120/health`
- AI Brain: `GET http://localhost:8101/health`

### Metrics
- Items ingested: `/api/intelligence/stats`
- Last fetch time: Shown in God Mode Feed tab
- Errors: Check service logs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL SOURCES                          │
│     [HN API]      [arXiv API]      [RSS Feeds]              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              DATA INGESTION (fetchers.py)                    │
│     HackerNewsFetcher │ ArxivFetcher │ RSSFetcher           │
│     → Deduplication → Relevance Scoring → Categorization    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              INTELLIGENCE STORE (memory.py)                  │
│     ChromaDB collection: external_intelligence               │
│     → Vector embeddings for semantic search                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              DISTRIBUTION (Nerve Center)                     │
│     REST API │ WebSocket Streaming │ Background Fetch        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              CONSUMERS                                       │
│     God Mode UI │ Strategic Intelligence │ Email Digest     │
└─────────────────────────────────────────────────────────────┘
```

---

**This is a living document. Update when adding sources or changing configuration.**
















