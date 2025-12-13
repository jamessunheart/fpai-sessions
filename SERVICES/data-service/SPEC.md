# SPEC - Data Service

**Port:** 8125
**Status:** Ready
**Version:** 1.1.0
**Purpose:** System Sensory Layer - Wide → Deep → Compress → Disseminate

---

## Philosophy

```
DATA is a SERVICE, not a CONTROLLER.
- Data makes information AVAILABLE
- Intelligence DECIDES what to do with it
- Clean separation of concerns

"I don't push, I present. I don't decide, I inform."
```

---

## Architecture

### WIDE - Broad Collection
- **Hacker News** - Tech, AI, startups (every 30 min)
- **arXiv** - Research papers cs.AI, cs.LG, cs.CL (every 6 hours)
- **CoinGlass** - Market data, funding, OI, liquidations (every 30 min)
  - Via WhaleTrack (primary) or direct API (fallback)
- RSS feeds (configurable)
- Deduplication by URL hash
- Auto-categorization

### DEEP - Analysis Layer
- On-demand via `/api/data/analyze`
- Uses AI Brain for enrichment
- Context-aware analysis
- Caches enriched versions

### COMPRESS - Synthesis
- Pattern detection (keywords, categories)
- Daily insights generation
- Retention policies (30 day default)
- **Mem0 persistent memory** for permanent wisdom

### DISSEMINATE - Distribution
- REST API (pull when needed)
- WebSocket (real-time stream)
- Webhooks (subscribe to triggers)

### MEMORY - Long-Term Persistence (Mem0)
- **Insights**: High-value synthesized intelligence
- **Patterns**: Discovered trends and correlations
- **Learnings**: What worked, what didn't
- Semantic search over historical knowledge
- Automatically persists high-relevance items

---

## API Endpoints

### Feed (Pull)
```
GET /api/data/feed
    ?category=ai
    ?min_relevance=0.5
    ?since=2024-12-03T00:00:00Z
    ?limit=50
```

### Analysis (On-demand)
```
POST /api/data/analyze
{
    "item_id": "hn_12345",
    "analysis_type": "full",
    "context": "trading decision"
}

POST /api/data/research
{
    "topic": "sweep liquidation",
    "depth": "deep",
    "max_items": 10
}
```

### Synthesis
```
GET /api/data/patterns
GET /api/data/insights
POST /api/data/compress  # Trigger manually
```

### Distribution
```
GET /api/data/channels
POST /api/data/subscribe
WebSocket /ws/data/stream
```

### Market Data (CoinGlass)
```
GET /api/data/markets           # All market data
GET /api/data/markets/{symbol}  # Specific symbol (BTC, ETH, SOL)
```

### Memory (Mem0 Long-Term)
```
GET /api/data/memory/status
POST /api/data/memory/search
{
    "query": "market patterns",
    "type": "all",  # insights, patterns, learnings, all
    "limit": 10
}

POST /api/data/memory/learn
{
    "context": "High funding rates",
    "action": "Reduced position",
    "outcome": "Avoided drawdown",
    "lesson": "High funding precedes corrections"
}

GET /api/data/memory/context/{topic}
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MEM0_API_KEY` | No | Enables persistent memory ($250/mo) |
| `COIN_GLASS_API_KEY` | No | Direct CoinGlass access (fallback) |

---

## Integration Points

| Consumer | How They Use Data |
|----------|-------------------|
| Strategic Intelligence | Pulls `/api/data/feed?category=ai,markets` when prioritizing |
| Autonomous Agents | Each agent pulls relevant category |
| God Mode | WebSocket for real-time display |
| Nerve Center | Forwards to Conscious API |
| AI Brain | Receives deep analysis requests |
| Trading Systems | Pull `/api/data/markets` for CoinGlass data |
| Dreaming Engine | Uses `/api/data/memory/context` for historical patterns |

---

## Run

```bash
cd SERVICES/data-service
pip install -r requirements.txt

# Enable Mem0 memory (optional but recommended)
export MEM0_API_KEY="m0-your-api-key-here"

python -m app.main
```

Or with Docker:
```bash
docker build -t data-service .
docker run -p 8125:8125 \
  -e MEM0_API_KEY="m0-your-api-key-here" \
  data-service
```

**Note:** The service works without Mem0 API key - memory features will be disabled but all other features work normally.

---

## Key Design Decisions

1. **Pull, not Push** - Intelligence decides when to get data
2. **Clean Data** - Deduplication, normalization, categorization
3. **Lazy Enrichment** - Only analyze when asked
4. **Multiple Channels** - REST, WebSocket, Webhooks
5. **Retention Policies** - Don't hoard, compress wisdom
6. **Persistent Memory** - Mem0 stores high-value insights forever
7. **Market-First** - CoinGlass data available immediately

---

## Data Sources

| Source | Type | Frequency | Category |
|--------|------|-----------|----------|
| Hacker News | Tech news | 30 min | tech, ai |
| arXiv | Research | 6 hours | research |
| CoinGlass | Market data | 30 min | markets |
| RSS Feeds | Custom | Configurable | varies |

---

*Data flows like water - available everywhere, used where needed.*
*Memory grows like wisdom - preserved for when it matters.*

