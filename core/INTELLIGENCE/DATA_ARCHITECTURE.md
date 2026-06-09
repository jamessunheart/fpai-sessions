# 📊 DATA - System Sensory Layer

**Philosophy:** Data is CLEAN and AVAILABLE. Intelligence decides when/how to use it.

---

## Architecture: Wide → Deep → Compress → Disseminate

```
                        ╔═══════════════════════════════════════════════════════╗
                        ║                      D A T A                          ║
                        ║              (Clean, Broad, Available)                ║
                        ╚═══════════════════════════════════════════════════════╝
                                              │
         ┌────────────────────────────────────┼────────────────────────────────────┐
         │                                    │                                    │
         ▼                                    ▼                                    ▼
    ╔═══════════╗                      ╔═══════════╗                      ╔═══════════╗
    ║   WIDE    ║                      ║   DEEP    ║                      ║ COMPRESS  ║
    ║           ║                      ║           ║                      ║           ║
    ║ • Collect ║                      ║ • Analyze ║                      ║ • Synth-  ║
    ║   broadly ║        Request       ║   with    ║     Processed        ║   esize   ║
    ║ • Research║ ◄───────────────────►║   AI Brain║ ─────────────────────►║ • Keep    ║
    ║ • Monitor ║     Deep Analysis    ║ • Enrich  ║                      ║   clean   ║
    ║ • Clean   ║                      ║ • Context ║                      ║ • Index   ║
    ╚═══════════╝                      ╚═══════════╝                      ╚═══════════╝
                                                                                │
                                                                                │
                                                                                ▼
                                                                         ╔═══════════╗
                                                                         ║DISSEMINATE║
                                                                         ║           ║
                                                                         ║ • Channels║
                                                                         ║ • Sub/Pub ║
                                                                         ║ • On-Pull ║
                                                                         ╚═══════════╝
                                                                                │
                    ┌───────────────────────────────────────────────────────────┤
                    │                           │                               │
                    ▼                           ▼                               ▼
          ┌─────────────────┐        ┌─────────────────┐              ┌─────────────────┐
          │   INTELLIGENCE  │        │   AUTONOMOUS    │              │    GOD MODE     │
          │   (Decides what │        │   AGENTS        │              │    (Human)      │
          │    to use/when) │        │   (Subscribe)   │              │                 │
          └─────────────────┘        └─────────────────┘              └─────────────────┘
```

---

## DATA Responsibilities (What We Build)

### 1. WIDE - Broad Collection
**Goal:** Cast a wide net on important topics

| Source | Topics | Frequency | Clean Output |
|--------|--------|-----------|--------------|
| Hacker News | Tech, AI, Startups | 30 min | `{title, url, score, category}` |
| arXiv | Research, AI/ML, Quantum | 6 hours | `{title, abstract, authors, categories}` |
| RSS Feeds | Configurable | 1 hour | `{title, summary, source, timestamp}` |
| CryptoPanic* | Crypto news | 15 min | `{title, sentiment, currencies}` |
| GitHub Trending* | New tools, repos | Daily | `{repo, stars, language, description}` |

*Future sources

**Cleaning Rules:**
- Remove duplicates (by URL hash)
- Normalize timestamps to UTC
- Extract entities (tokens, companies, people)
- Assign preliminary category
- Score relevance (keyword matching)

### 2. DEEP - Analysis Layer
**Goal:** Enrich data when Intelligence requests it

```python
# Intelligence calls DATA for deep analysis
POST /api/data/analyze
{
    "item_id": "hn_12345",
    "analysis_type": "full",  # or "summary", "sentiment", "entities"
    "context": "trading decision"  # helps AI Brain focus
}

# DATA works with AI Brain to enrich
Response:
{
    "original": {...},
    "enriched": {
        "summary": "...",
        "sentiment": 0.7,
        "entities": ["Bitcoin", "SEC", "ETF"],
        "relevance_to_context": 0.85,
        "key_insights": ["..."],
        "related_items": ["hn_12346", "arxiv_789"]
    }
}
```

### 3. COMPRESS - Synthesis & Storage
**Goal:** Keep only what's valuable, indexed and queryable

**Storage:**
```
ChromaDB Collections:
├── raw_intelligence      # All collected items (30 day retention)
├── enriched_intelligence # Deep-analyzed items (90 day retention)
├── synthesized_insights  # Compressed wisdom (permanent)
└── patterns              # Discovered patterns (permanent)
```

**Compression Operations:**
- Daily: Remove low-relevance items (< 0.3 score)
- Weekly: Synthesize patterns across items
- Monthly: Generate trend reports

### 4. DISSEMINATE - Distribution Channels
**Goal:** Data available to whoever needs it, when they need it

**Pull Channels (Intelligence decides when):**
```
GET /api/data/feed
    ?category=ai,markets
    &min_relevance=0.5
    &since=2024-12-03T00:00:00Z
    &limit=50

GET /api/data/search
    ?query=sweep+liquidation
    &collection=enriched_intelligence

GET /api/data/patterns
    ?timeframe=7d
    &type=emerging
```

**Push Channels (Subscribe for updates):**
```
WebSocket /ws/data/stream
    Subscribe: {"categories": ["ai", "markets"], "min_relevance": 0.7}
    Receive: Real-time high-relevance items

Webhook /api/data/subscribe
    Register callback URL for specific triggers
```

**Channel Registry:**
```python
DISSEMINATION_CHANNELS = {
    "nerve_center": {
        "type": "internal",
        "endpoint": "http://localhost:8120/api/ingest",
        "triggers": ["high_relevance", "security_alert"]
    },
    "strategic_intelligence": {
        "type": "on_request",
        "endpoint": "http://localhost:8500/api/v1/signals",
        "note": "Intelligence pulls when it needs signals"
    },
    "god_mode": {
        "type": "websocket",
        "endpoint": "ws://localhost:8300/ws/data",
        "triggers": ["all"]
    },
    "agents": {
        "type": "on_request",
        "endpoint": "/api/data/for-agent/{type}",
        "note": "Each agent pulls its relevant feed"
    }
}
```

---

## Intelligence's Role (NOT Data's job)

Intelligence decides:
- ✅ **When** to request data
- ✅ **What** data to prioritize
- ✅ **How** to act on data
- ✅ **Which** patterns matter

Data provides:
- ✅ Clean, structured information
- ✅ On-demand analysis (via AI Brain)
- ✅ Reliable availability
- ✅ Multiple access patterns (pull/push/subscribe)

---

## API Design

### Core Data Endpoints

```yaml
# WIDE - Collection Status
GET /api/data/sources
  # Returns: all sources, last fetch, item counts

GET /api/data/feed
  # Returns: clean, categorized items
  # Params: category, min_relevance, since, limit

# DEEP - Analysis (On Request)
POST /api/data/analyze
  # Body: {item_id, analysis_type, context}
  # Returns: enriched item with AI analysis

POST /api/data/research
  # Body: {topic, depth: "surface|moderate|deep"}
  # Returns: compiled research on topic

# COMPRESS - Synthesized Data
GET /api/data/patterns
  # Returns: discovered patterns, trends

GET /api/data/insights
  # Returns: compressed wisdom, key takeaways

# DISSEMINATE - Distribution
GET /api/data/channels
  # Returns: available dissemination channels

POST /api/data/subscribe
  # Body: {callback_url, triggers, filters}
  # Registers subscriber

WebSocket /ws/data/stream
  # Real-time feed with subscription filters
```

---

## Implementation Priority

### Phase 1: Clean Foundation (Current)
- [x] Wide collection (HN, arXiv, RSS)
- [x] Basic cleaning & categorization
- [x] Storage in Nerve Center
- [x] REST API access

### Phase 2: Deep Integration
- [ ] `/api/data/analyze` endpoint (calls AI Brain)
- [ ] `/api/data/research` for on-demand deep dives
- [ ] Enrichment pipeline

### Phase 3: Compress & Retain
- [ ] Pattern detection (automated)
- [ ] Insight synthesis (daily)
- [ ] Retention policies
- [ ] Wisdom preservation

### Phase 4: Smart Dissemination
- [ ] Channel registry
- [ ] WebSocket streaming
- [ ] Subscriber management
- [ ] Trigger-based distribution

---

## Key Principle

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   DATA is a SERVICE, not a CONTROLLER.                             │
│                                                                     │
│   • Data makes information AVAILABLE                                │
│   • Intelligence DECIDES what to do with it                         │
│   • Clean separation of concerns                                    │
│                                                                     │
│   "I don't push, I present. I don't decide, I inform."             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Files

| File | Purpose |
|------|---------|
| `SERVICES/nerve_center/server.py` | Current data hub |
| `SERVICES/ai-brain/app/fetchers.py` | Wide collection |
| `SERVICES/ai-brain/app/memory.py` | Storage layer |
| `core/INTELLIGENCE/DATA_ARCHITECTURE.md` | This design doc |

---

*Data is the eyes and ears. Intelligence is the brain that decides what to see and hear.*















