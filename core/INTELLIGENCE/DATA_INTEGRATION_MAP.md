# 🧠 Data Intelligence Engine - System Integration Map

**Generated:** 2025-12-03
**Purpose:** Map how Data Intelligence Engine enhances the entire FPAI ecosystem

---

## Current System Architecture

```
                                 ┌─────────────────────────────────┐
                                 │       HUMAN INTERFACE           │
                                 │         (God Mode)              │
                                 │  ✅ Conscious Dashboard added   │
                                 └───────────────┬─────────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
         ┌──────────────────┐         ┌──────────────────┐        ┌──────────────────┐
         │   AI BRAIN       │         │  NERVE CENTER    │        │   STRATEGIC      │
         │   Port 8101      │         │   Port 8120      │        │   INTELLIGENCE   │
         │                  │         │                  │        │   Port 8500      │
         │ • Multi-model AI │         │ • WebSocket hub  │        │                  │
         │ • RAG Memory     │◄───────►│ • Event ingestion│◄──────►│ • Priority score │
         │ • Skills/Prompts │         │ • Conscious API  │        │ • Mission queue  │
         │ • Embeddings     │         │ • Intelligence   │        │ • World model    │
         └────────┬─────────┘         └────────┬─────────┘        └────────┬─────────┘
                  │                            │                            │
                  │    ╔════════════════════════════════════════════╗      │
                  │    ║     DATA INTELLIGENCE ENGINE               ║      │
                  │    ║     (Our New System)                       ║      │
                  └───►║                                            ║◄─────┘
                       ║  External Sources:                         ║
                       ║  • Hacker News (tech trends)              ║
                       ║  • arXiv (research, horizon scanning)     ║
                       ║  • RSS feeds (configurable)               ║
                       ║                                            ║
                       ║  Internal Sources:                         ║
                       ║  • System events (Nerve Center)           ║
                       ║  • Trading signals (WhaleTrack)           ║
                       ║  • GPU fleet status (162.0.208.88)        ║
                       ╚════════════════════════════════════════════╝
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │  AUTONOMOUS      │  │   MISSION HUB    │  │   WHALETRACK     │
         │  AGENTS          │  │   Port 8700      │  │   Port 8600      │
         │                  │  │                  │  │                  │
         │ • Monitoring     │  │ • Task dispatch  │  │ • Sweep trading  │
         │ • Treasury       │  │ • Human bridge   │  │ • Market signals │
         │ • Opportunity    │  │ • Job tracking   │  │ • APR tracking   │
         │ • Knowledge      │  │                  │  │                  │
         └──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## ✅ Already Integrated (What We Built)

| Integration | Status | Value |
|-------------|--------|-------|
| Nerve Center Conscious API | ✅ Built | All 4 pillars exposed via REST |
| God Mode Dashboard | ✅ Built | Visual interface for Conscious Architecture |
| External Intelligence Fetchers | ✅ Built | HN, arXiv, RSS feeds |
| AI Brain Memory | ✅ Built | ChromaDB `external_intelligence` collection |
| Synthesis Skills | ✅ Built | Market news, research, tech trends |
| APR Tracking | ✅ Built | ROI calculation for all strategies |
| Pattern Detection | ✅ Built | Keyword clustering, trend identification |
| Proposal Generation | ✅ Built | Action recommendations from patterns |

---

## 🔥 High-Impact Enhancements (Immediate)

### 1. Strategic Intelligence Auto-Push
**Gap:** Data flows to Nerve Center but doesn't reach Strategic Intelligence
**Enhancement:** Auto-push high-relevance items to `/api/v1/signals`

```python
# In nerve_center/server.py - Add to intelligence_fetch_loop()
async def auto_push_to_strategic():
    high_relevance = [i for i in _intelligence_cache if i.get("relevance_score", 0) >= 0.7]
    async with httpx.AsyncClient() as client:
        for item in high_relevance[:5]:  # Top 5 per cycle
            await client.post("http://localhost:8500/api/v1/signals", json={
                "source": item["source"],
                "content": f"{item['title']}: {item.get('summary', '')[:200]}",
                "url": item.get("source_url"),
                "relevance_score": item.get("relevance_score"),
                "category": item.get("category")
            })
```

**Impact:** Strategic Intelligence gets external signals for priority scoring

---

### 2. Autonomous Agent Knowledge Feed
**Gap:** Agents lack external intelligence for decision-making
**Enhancement:** Create agent-specific intelligence endpoints

```
GET /api/intelligence/for-agent/{agent_type}

agent_type:
  - "opportunity" → markets, crypto, DeFi signals
  - "treasury" → yield opportunities, protocol updates
  - "monitoring" → security alerts, service updates
  - "knowledge" → research, patterns, learnings
```

**Impact:** Agents make better decisions with external data

---

### 3. Morning Briefing Intelligence Digest
**Gap:** Overnight optimizer doesn't include external intelligence
**Enhancement:** Feed intelligence digest to morning_briefing.md

```python
# In autonomous-night-optimizer.py
async def generate_intelligence_digest():
    resp = await httpx.get("http://localhost:8120/api/intelligence/digest")
    digest = resp.json()
    return f"""
## 🧠 Intelligence Digest (Overnight)

### Top AI/Tech Stories
{digest['digest']}

### Trending Topics
{', '.join(t['topic'] for t in digest['trending'][:5])}

### High-Relevance Items: {digest['items_analyzed']}
"""
```

**Impact:** You wake up to curated intelligence + system improvements

---

### 4. Trading Signal Enhancement
**Gap:** Sweep detection lacks market context
**Enhancement:** Feed market intelligence to WhaleTrack

```
POST /api/sweep-traders/market-context
{
    "market_sentiment": "bullish", 
    "trending_tokens": ["BTC", "SOL"],
    "news_volume": 42,
    "fear_greed_proxy": 65
}
```

**Impact:** Trading decisions informed by broader market context

---

## 🎯 Medium-Priority Integrations

### 5. GPU Fleet Intelligence
**Location:** 162.0.208.88:8115 (Scaling API)
**Enhancement:** Include compute status in IDENTITY pillar

```python
# Already have this in _get_compute_state(), ensure it's called
async def _get_compute_state():
    # GET http://162.0.208.88:8115/api/all-providers
    # GET http://162.0.208.88:11434/api/tags (Ollama models)
```

---

### 6. Dreaming Engine Nightly Synthesis
**Gap:** DreamingEngine exists but isn't scheduled
**Enhancement:** Add cron job for nightly dreams

```bash
# /etc/cron.d/fpai-dreaming
0 3 * * * fpai python3 /opt/fpai/services/ai-brain/app/dreaming.py --run-cycle
```

**Impact:** Pattern discovery runs overnight, insights ready in morning

---

### 7. Horizon Scanner → Long-Term Planning
**Gap:** 3-5 year signals not feeding into mission planning
**Enhancement:** Quarterly horizon reports

```python
# New endpoint: GET /api/conscious/thinking/horizon-quarterly
# Aggregates 90 days of weak signals, generates strategic recommendations
```

---

## 📊 Data Flow Enhancement Summary

```
BEFORE (Isolated):
┌─────────┐    ┌──────────────┐    ┌─────────────┐
│ HN/arXiv│───►│ Nerve Center │    │ Strategies  │ (no connection)
└─────────┘    └──────────────┘    └─────────────┘

AFTER (Integrated):
┌─────────┐    ┌──────────────┐    ┌─────────────────┐    ┌───────────┐
│ HN/arXiv│───►│ Nerve Center │───►│ Strategic Intel │───►│ Missions  │
└─────────┘    │              │    └────────┬────────┘    └───────────┘
               │ Intelligence │             │
               │ Feed         │             ▼
               │              │    ┌─────────────────┐
               │              │───►│ Autonomous      │
               └───────┬──────┘    │ Agents          │
                       │           └─────────────────┘
                       │
                       ▼
               ┌──────────────┐    ┌─────────────────┐
               │ God Mode     │───►│ Human Decision  │
               │ Conscious    │    │ Making          │
               │ Dashboard    │    └─────────────────┘
               └──────────────┘
```

---

## 🚀 Quick Wins (< 1 hour each)

| Enhancement | File to Modify | Impact |
|-------------|----------------|--------|
| Auto-push to Strategic Intel | `nerve_center/server.py` | High - enables autonomous prioritization |
| Add to morning briefing | `autonomous-night-optimizer.py` | High - human sees intelligence daily |
| GPU status in Identity | Already done in Nerve Center | Medium - visibility |
| Schedule Dreaming | Cron job | Medium - overnight pattern discovery |

---

## 🔗 Service Connection Matrix

| Service | Receives From | Sends To | Status |
|---------|--------------|----------|--------|
| Nerve Center | External APIs, System Events | God Mode, Strategic Intel, Agents | ✅ Hub |
| Strategic Intel | Nerve Center signals | Mission Hub, Orchestrator | 🔄 Need auto-push |
| AI Brain | Questions, Indexing requests | Answers, Embeddings | ✅ Works |
| God Mode | All Conscious endpoints | Human decisions | ✅ Dashboard built |
| WhaleTrack | Market data | Trading performance | 🔄 Need context feed |
| Agents | Intelligence feed | System improvements | 🔄 Need agent endpoints |
| Mission Hub | Priority queue | Human tasks | ✅ Existing |

---

## Next Steps (Recommended Order)

1. **[ ] Auto-push to Strategic Intelligence** - 30 min
   - Add to `intelligence_fetch_loop()` in Nerve Center
   - Strategic Intelligence will start scoring external signals

2. **[ ] Agent Intelligence Endpoints** - 45 min
   - Add `/api/intelligence/for-agent/{type}` 
   - Filters intelligence by agent specialty

3. **[ ] Morning Briefing Integration** - 30 min
   - Add intelligence digest to `autonomous-night-optimizer.py`
   - You get curated intel every morning

4. **[ ] Schedule Dreaming Engine** - 15 min
   - Add cron job for 3am daily
   - Pattern discovery runs overnight

5. **[ ] WhaleTrack Market Context** - 45 min
   - Create endpoint for market sentiment
   - Inform trading decisions

---

*This map shows how the Data Intelligence Engine can become the sensory system for the entire FPAI ecosystem, feeding every decision-making component with valuable, curated intelligence.*















