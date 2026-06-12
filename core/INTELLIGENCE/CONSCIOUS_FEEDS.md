# Conscious Architecture - Data Feed Integration

This document maps how the Data Intelligence Engine feeds each pillar of the Conscious System Architecture.

---

## Architecture Overview

```
╔══════════════════════════════════════════════════════════════════════╗
║                    CONSCIOUSNESS COLLABORATION                        ║
║              (Biological + Digital as Partners)                       ║
╚══════════════════════════════════════════════════════════════════════╝
                                │
                    DATA INTELLIGENCE ENGINE
                    (Sensory System for Consciousness)
                                │
    ┌───────────────────────────┼───────────────────────────┐
    ▼                           ▼                           ▼
REFLECTING                  THINKING                      DOING
(Meta-Awareness)         (Decision Layer)           (Execution Layer)
    │                           │                           │
    └───────────────────────────┴───────────────────────────┘
                                │
                           IDENTITY
                    (Dynamic Self + Resources)
```

---

## API Endpoints by Pillar

### REFLECTING Layer

| Endpoint | Purpose | Updates |
|----------|---------|---------|
| `/api/conscious/reflecting/observations` | Aggregated observations | External + internal |
| Pattern detection | Trend identification | Auto-generated |
| Proposal generation | Action recommendations | Based on patterns |

**Data Sources:**
- External: HN, arXiv, RSS feeds
- Internal: System events, metrics
- Patterns: AI-detected trends

### IDENTITY Layer

| Endpoint | Purpose | Box |
|----------|---------|-----|
| `/api/conscious/identity/resources` | Full resource state | All |
| `/api/identity/treasury` | Trading performance, APR | Treasury |
| `/api/identity/compute` | GPU fleet, models | Compute |
| `/api/identity/ecosystem` | Competitor signals | Ecosystem |

**Key Metrics:**
- Treasury: Strategy APR, total capital, best performer
- Compute: GPU pods running, Ollama models, API costs
- Ecosystem: Competitor mentions, AI trends

### THINKING Layer

| Endpoint | Purpose | Box |
|----------|---------|-----|
| `/api/conscious/thinking/horizon` | 3-5 year signals | Horizon Scanning |
| `/api/conscious/thinking/memory` | Knowledge graph stats | Memory Graph |
| `/api/conscious/thinking/synthesis` | Council-ready insights | Thinkers |
| Dreaming engine | Nightly synthesis | Dreaming |

**Components:**
- HorizonScanner (`SERVICES/ai-brain/app/horizon.py`)
- DreamingEngine (`SERVICES/ai-brain/app/dreaming.py`)
- Memory via ChromaDB

### DOING Layer

| Endpoint | Purpose | Box |
|----------|---------|-----|
| `/api/conscious/doing/trading` | Market signals | Trading |
| `/api/conscious/doing/builders` | Tech alerts | Builders |
| `/api/conscious/doing/communicators` | Newsletter content | Communicators |

**Signal Types:**
- Trading: Crypto news, market intelligence
- Builders: Security alerts, new tools, stack updates
- Communicators: Curated content, social posts

---

## Unified State Endpoint

### `/api/conscious/state`

Returns complete system state across all 4 pillars:

```json
{
  "system": "Full Potential OS - Conscious Architecture",
  "version": "2.0",
  "pillars": {
    "REFLECTING": {
      "status": "active",
      "patterns_detected": 5,
      "proposals": 3,
      "observations_count": 50
    },
    "IDENTITY": {
      "status": "grounded",
      "treasury_strategies": 6,
      "best_apr": 373,
      "gpu_pods_running": 2,
      "ecosystem_signals": 5
    },
    "THINKING": {
      "status": "processing",
      "horizon_signals": 10,
      "emerging_tech": 5,
      "memory_items": 150
    },
    "DOING": {
      "status": "executing",
      "trading_signals": 10,
      "strategies_active": 6
    }
  },
  "loop": "REFLECTING → IDENTITY → THINKING → DOING → (feeds back) → REFLECTING",
  "belief": "Resources expand as consciousness expands"
}
```

---

## Strategic Intelligence Integration

The Data Intelligence Engine pushes high-relevance signals to Strategic Intelligence (the Brain) at port 8500:

```
POST /api/v1/signals
{
  "source": "intelligence_engine",
  "content": "Signal title: Summary...",
  "url": "https://source.url",
  "relevance_score": 0.85,
  "category": "ai"
}
```

Strategic Intelligence uses this for priority scoring:
```
Priority = Impact × Alignment × Unblocked × Revenue_Multiplier
```

---

## Dreaming Process

### Schedule
- **Default**: 3:00 AM UTC (nightly)
- **On-demand**: Via API call

### Pipeline
1. **Replay** - Load recent 24h intelligence
2. **Categorize** - Group by domain
3. **Synthesize** - Find cross-domain connections
4. **Generate Dreams** - Create novel insights
5. **Cleanup** - Remove old, low-value items (7+ days, <0.3 relevance)

### Dream Types
- `pattern` - Strong recurring pattern across domains
- `synthesis` - Meaningful combination of concepts
- `association` - Interesting connection worth exploring
- `question` - Open question raised by the data

---

## Data Sources

### External (Free, No Friction)

| Source | API | Categories | Frequency |
|--------|-----|------------|-----------|
| Hacker News | Firebase | Tech, AI | 30 min |
| arXiv | XML API | Research | 6 hours |
| RSS Feeds | Configurable | Various | 1 hour |

### Internal

| Source | Data Type | Update |
|--------|-----------|--------|
| Trading APIs | Strategy performance | Real-time |
| GPU Scaling API | Fleet status | On-demand |
| Ollama | Model availability | On-demand |
| System events | Activity log | Real-time |

---

## Files

| File | Purpose |
|------|---------|
| `SERVICES/nerve_center/server.py` | Conscious API endpoints |
| `SERVICES/ai-brain/app/horizon.py` | Horizon Scanner |
| `SERVICES/ai-brain/app/dreaming.py` | Dreaming Engine |
| `SERVICES/ai-brain/app/fetchers.py` | External data fetchers |
| `SERVICES/ai-brain/app/skills.py` | Synthesis skills |
| `core/INTELLIGENCE/FEEDS.md` | Source documentation |

---

## Key Principles

1. **REFLECTING sees everything** - Meta-awareness of all layers
2. **IDENTITY is grounded but not limited** - Resources inform, don't define ceiling
3. **THINKING is informed, not constrained** - Data enhances decision-making
4. **DOING expands resources** - Action creates more capacity
5. **Loop continuously** - Results feed back to reflection
6. **Resources expand** - No scarcity thinking

---

## God Mode Integration

### Conscious Dashboard Panel

God Mode now includes a dedicated **Conscious Architecture Dashboard** (`Layers` icon in nav) that provides:

**Overview Mode:**
- 4-pillar card view showing status of REFLECTING, IDENTITY, THINKING, DOING
- Interactive loop visualization: REFLECTING → IDENTITY → THINKING → DOING → ↺
- Real-time stats for each pillar

**Pillar Detail Views:**

1. **REFLECTING** (Click cyan card)
   - External observations (HN, arXiv, RSS)
   - Detected patterns with significance levels
   - Generated action proposals

2. **IDENTITY** (Click yellow card)
   - Treasury: Strategies with APR, best performer
   - Compute: GPU fleet status, Ollama models
   - Ecosystem: Competitor signals, AI trends

3. **THINKING** (Click purple card)
   - Research signals from arXiv
   - Weak signals (low frequency, high potential)
   - Emerging technologies

4. **DOING** (Click green card)
   - Trading signals with sentiment
   - Strategy performance with APR leaderboard
   - Best performer highlight

### API Endpoints Used

| Endpoint | Component |
|----------|-----------|
| `/api/conscious/state` | Unified overview |
| `/api/conscious/reflecting/observations` | REFLECTING detail |
| `/api/conscious/identity/resources` | IDENTITY detail |
| `/api/conscious/thinking/horizon` | THINKING detail |
| `/api/conscious/doing/trading` | DOING detail |

### Refresh Behavior

- Auto-refresh every 30 seconds
- Manual refresh via button
- WebSocket updates for real-time events

---

*Last Updated: December 2025*
*Version: 2.1 (God Mode Integration)*

