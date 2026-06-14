# 📊 Data System Map (Visual + How To Use)

**Purpose:** A single, visual “mental model” for how the FPAI data system works and how to operate it day-to-day.  
**Source of truth for service locations:** `docs/coordination/SERVICE_REGISTRY.md`

---

## Visual Map (End-to-End Flywheel)

```mermaid
flowchart LR
  %% SOURCES
  HN[Hacker News] -->|collect| DS[Data Service :8125]
  ARX[arXiv] -->|collect| DS
  RSS[RSS Feeds] -->|collect| DS
  CG[CoinGlass via WhaleTrack] -->|collect| DS

  %% AI ENRICHMENT
  DS -->|analyze/research (on-demand)| AIB[AI Brain :8101 (Secondary)]

  %% DISTRIBUTION
  DS -->|events + summaries| NC[Nerve Center :8120]
  NC -->|signals + outcomes| SI[Strategic Intelligence :8500]

  %% WORK OBJECTS
  NC -->|drop intents (files)| INTENTS[docs/coordination/intents/*.json]

  %% EXECUTION (human/agents/services)
  INTENTS -->|execute| EXEC[Humans + Agents + Services]
  EXEC -->|record outcomes| OUT[Outcome Ledger (Nerve Center)]
  OUT -->|learn (Mem0)| DS
  OUT -->|signal| SI

  %% UI
  NC -->|unified state| GM[God Mode :8300]
  DS -->|feeds/patterns| GM
  SI -->|priorities| GM
```

---

## Mind Map (System + Flows)

> If your Markdown renderer supports Mermaid mindmaps, this is the quickest “whole system at once” view.

```mermaid
mindmap
  root((FPAI DATA SYSTEM))
    Sources
      Hacker News
      arXiv
      RSS Feeds
      CoinGlass (via WhaleTrack)
    Data Service (:8125)
      Wide Collection
      Clean + Categorize + Relevance
      Patterns + Insights
      Deep Analysis (on-demand)
        AI Brain (:8101 secondary)
    Nerve Center (:8120)
      Pipeline Health + Freshness
      Action Digest (daily + on-demand)
      Intents (work objects)
        docs/coordination/intents/digest-*.json
      Outcome Ledger (feedback)
        docs/coordination/outcomes/ledger.jsonl
    Strategic Intelligence (:8500)
      Signals ingestion
      Prioritization + Dispatch
    Execution
      Humans
      Agents
      Services (WhaleTrack / AI Automation)
    UI
      God Mode (:8300)
        Data tab (operate the flywheel)
    Flows
      Collect → Store
      Analyze (AI Brain) → Enrich
      Digest → Intents
      Execute → Outcome
      Outcome → Learning → Better Digest
```

### Fallback Mind Map (always readable)

```text
FPAI DATA SYSTEM
├─ Sources (HN, arXiv, RSS, CoinGlass)
│   └─ (collect)
├─ Data Service (8125)
│   ├─ Wide collection + cleaning
│   ├─ Patterns + Insights
│   └─ Deep analysis (calls AI Brain 8101 on-demand)
│       └─ (enrich)
├─ Nerve Center (8120)
│   ├─ Pipeline health + freshness (are we blind?)
│   ├─ Action Digest (Top actions)
│   ├─ Intents (work objects dropped as files)
│   └─ Outcome ledger (feedback loop)
│       └─ (learn)
├─ Strategic Intelligence (8500)
│   └─ Ingests signals/outcomes → prioritizes → dispatches
└─ God Mode (8300)
    └─ Data tab: run digest, see intents, record outcomes
```

## “How Do I Work With It?” (Operator Workflow)

### 1) Check the system is seeing clearly (freshness)
- **Nerve Center pipeline health:** `GET /api/intelligence/pipeline/health`
- Look for **red/yellow**, and which sources are stale (HN/arXiv/RSS/CoinGlass).

### 2) Generate actions (the daily “Action Digest”)
- **Run digest now:** `POST /api/intelligence/digest/run`
  - Generates **Top 10 actions** (trading + leadgen + system)
  - Can **push** into Strategic Intelligence
  - Can **create intents** (work objects) automatically

### 3) Turn actions into work (intents)
- Intents are dropped to: `docs/coordination/intents/digest-*.json`
- These are the “tickets” the system can execute (human + agents).

### 4) Execute (human or agent), then record results
- **Record outcome:** `POST /api/outcomes/record`
- Outcomes are persisted to: `docs/coordination/outcomes/ledger.jsonl`
- Outcomes automatically:
  - feed **learning** into Data Service (Mem0) (best-effort)
  - feed **signals** into Strategic Intelligence (best-effort)

### 5) Next digest improves
The next digest sees recent outcomes and adjusts recommendations (closed-loop learning).

---

## Key Operator Endpoints (Quick Reference)

### Nerve Center (8120)
- `GET /health`
- `GET /api/conscious/state`
- `GET /api/intelligence/pipeline/health`
- `POST /api/intelligence/digest/run`
- `GET /api/intelligence/digest/latest`
- `GET /api/intelligence/intents/recent`
- `POST /api/outcomes/record`
- `GET /api/outcomes/recent`
- `GET /api/outcomes/stats`

### Data Service (8125)
- `GET /health`
- `GET /api/data/feed`
- `GET /api/data/patterns`
- `GET /api/data/insights`
- `POST /api/data/memory/learn` (learning capture)

### Strategic Intelligence (8500)
- `GET /health`
- `POST /api/v1/signals`
- `GET /api/v1/signals/recent`

---

## Example (Run Digest → Create Intents)

```bash
curl -X POST "http://198.54.123.234:8120/api/intelligence/digest/run" \
  -H "Content-Type: application/json" \
  -d '{
    "hours": 24,
    "min_relevance": 0.6,
    "limit": 80,
    "mode": "both",
    "push_to_strategic": true,
    "create_intents": true,
    "max_intents": 3,
    "intent_ttl_hours": 24
  }'
```

## Example (Record Outcome → Learn)

```bash
curl -X POST "http://198.54.123.234:8120/api/outcomes/record" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "leadgen",
    "action_title": "Leadgen: convert into outreach angle — …",
    "outcome": "positive",
    "metric_name": "leads_booked",
    "metric_value": 1,
    "notes": "Booked 1 call from the outreach angle.",
    "related_urls": [],
    "push_to_mem0": true,
    "push_to_strategic": true
  }'
```


