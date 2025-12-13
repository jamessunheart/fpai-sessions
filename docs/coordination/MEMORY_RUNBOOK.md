# Memory System Operations Runbook

## Overview

The FPAI Memory System provides persistent, semantic memory for AI decision-making.

**Components:**
- **Mem0 Cloud** - Semantic search and long-term persistence
- **Data Service** - Memory API (port 8125 on primary server)
- **Retrieval Tracker** - Quality scoring and hygiene

---

## Quick Reference

### Check Memory System Health

```bash
# Get overall memory stats
curl http://198.54.123.234:8125/api/memory/stats | jq

# Get system memory (RAM) usage
curl http://198.54.123.234:8125/api/memory/system-stats | jq

# God Mode memory panel
curl http://198.54.123.234:8120/api/memory | jq
```

### Store a Memory

```bash
# Store an insight
curl -X POST http://198.54.123.234:8125/api/memory/insight \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Trading Pattern",
    "content": "SOL tends to pump after BTC consolidation",
    "category": "trading",
    "relevance": 0.9
  }'

# Store a learning
curl -X POST http://198.54.123.234:8125/api/memory/learn \
  -H "Content-Type: application/json" \
  -d '{
    "context": "Deployed new version",
    "action": "Deployed without backup",
    "outcome": "Had to rollback manually",
    "lesson": "Always backup before deploy"
  }'

# Store a pattern
curl -X POST http://198.54.123.234:8125/api/memory/pattern \
  -H "Content-Type: application/json" \
  -d '{
    "pattern_type": "technical",
    "condition": "When funding rate > 0.05%",
    "action": "Consider shorting",
    "confidence": 0.8
  }'
```

### Search Memories

```bash
# Search all memory types
curl -X POST http://198.54.123.234:8125/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "trading strategies", "limit": 10}'

# Get wisdom for a topic (patterns + learnings + past decisions)
curl http://198.54.123.234:8125/api/memory/wisdom/trading
```

---

## Bootstrap Process

### Initial Load (First Time Setup)

```bash
# SSH to primary server
ssh root@198.54.123.234
# or via Tailscale
ssh root@100.122.184.66

# Set Mem0 API key
export MEM0_API_KEY="m0-xxx"

# Run bootstrap script
cd /opt/fpai
python3 orchestration/tools/bootstrap_memory.py

# Verify
curl http://localhost:8125/api/memory/stats | jq '.total_operations'
```

### Re-bootstrap (After Adding New Knowledge)

```bash
# Dry run first
python3 orchestration/tools/bootstrap_memory.py --dry_run

# Run for specific files only
python3 orchestration/tools/bootstrap_memory.py --files patterns,learnings
```

---

## Memory Hygiene

### Weekly Maintenance

```bash
# Run all hygiene tasks
curl -X POST http://198.54.123.234:8125/api/memory/hygiene/weekly

# Response shows:
# - cleanup: removed unused memories
# - consolidation: merged similar memories
# - export: archived to markdown
```

### Manual Cleanup

```bash
# Cleanup old memories (90+ days, <3 retrievals)
curl -X POST http://198.54.123.234:8125/api/memory/hygiene/cleanup \
  -H "Content-Type: application/json" \
  -d '{"days": 90, "min_retrievals": 3, "dry_run": false}'

# Consolidate similar memories
curl -X POST http://198.54.123.234:8125/api/memory/hygiene/consolidate \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

### Export High-Value Memories

```bash
# Export to markdown for Git archiving
curl -X POST http://198.54.123.234:8125/api/memory/hygiene/export \
  -H "Content-Type: application/json" \
  -d '{"memory_type": "insights", "limit": 20}'
```

---

## Debugging

### Memory Not Found Issues

1. Check if Mem0 API key is set:
```bash
# On server
echo $MEM0_API_KEY

# In Data Service logs
journalctl -u fpai-data-service | grep "Mem0"
```

2. Check Mem0 connectivity:
```bash
curl -H "Authorization: Token $MEM0_API_KEY" \
  https://api.mem0.ai/v1/memories/ 2>/dev/null | head
```

### High Memory Usage

1. Check Data Service memory:
```bash
curl http://198.54.123.234:8125/api/memory/system-stats | jq '.process.rss_mb'
```

2. Restart if over 500MB:
```bash
systemctl restart fpai-data-service
```

### Search Returns Empty

1. Check Mem0 enabled:
```bash
curl http://198.54.123.234:8125/api/memory/stats | jq '.enabled'
```

2. Run bootstrap if empty:
```bash
python3 orchestration/tools/bootstrap_memory.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MEMORY SYSTEM                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │  WhaleTrack │     │ I-Proactive │     │  God Mode   │  │
│   │  (Trading)  │     │(Decisions)  │     │ (Dashboard) │  │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘  │
│          │                   │                   │         │
│          └───────────────────┼───────────────────┘         │
│                              │                             │
│                              ▼                             │
│                    ┌─────────────────┐                     │
│                    │  Data Service   │                     │
│                    │  (Port 8125)    │                     │
│                    │                 │                     │
│                    │ • Memory Router │                     │
│                    │ • Learning API  │                     │
│                    │ • Hygiene Jobs  │                     │
│                    └────────┬────────┘                     │
│                             │                              │
│              ┌──────────────┼──────────────┐               │
│              │              │              │               │
│              ▼              ▼              ▼               │
│     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│     │   Mem0 API  │ │ Local JSON  │ │  Markdown   │       │
│     │  (Semantic) │ │ (Keywords)  │ │   (Docs)    │       │
│     └─────────────┘ └─────────────┘ └─────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Memory Types Reference

| Type | User ID | Use Case |
|------|---------|----------|
| insight | fpai_insights | Observations, trends |
| pattern | fpai_patterns | Conditions → Actions |
| learning | fpai_learnings | Context → Outcome → Lesson |
| decision | fpai_decisions | Past decisions + results |
| context | fpai_context | Temporary context |

---

## API Endpoints Reference

### Core Operations
- `POST /api/memory/store` - Store any memory type (auto-classifies)
- `POST /api/memory/search` - Search all types
- `GET /api/memory/wisdom/{topic}` - Get aggregated wisdom

### Specific Types
- `POST /api/memory/insight` - Store insight
- `POST /api/memory/pattern` - Store pattern
- `POST /api/memory/learn` - Store learning
- `POST /api/memory/decision` - Store decision
- `POST /api/memory/outcome` - Link outcome to decision

### Learning Capture
- `POST /api/learning/trade` - Capture trade learning
- `POST /api/learning/deployment` - Capture deployment learning

### Hygiene
- `POST /api/memory/hygiene/weekly` - Full maintenance
- `POST /api/memory/hygiene/cleanup` - Remove unused
- `POST /api/memory/hygiene/consolidate` - Merge duplicates
- `POST /api/memory/hygiene/export` - Archive to markdown

### Stats
- `GET /api/memory/stats` - Memory statistics
- `GET /api/memory/system-stats` - Process memory usage
- `POST /api/memory/track-retrieval` - Manual tracking

---

## Cron Jobs (Recommended)

```cron
# Weekly hygiene - Sunday 3am
0 3 * * 0 curl -X POST http://localhost:8125/api/memory/hygiene/weekly

# Daily export of insights - 4am
0 4 * * * curl -X POST http://localhost:8125/api/memory/hygiene/export -H "Content-Type: application/json" -d '{"memory_type": "insights", "limit": 10}'
```

---

## Troubleshooting Matrix

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 401 on Mem0 calls | Invalid API key | Check MEM0_API_KEY env var |
| Empty search results | No memories loaded | Run bootstrap |
| High latency (>2s) | Mem0 rate limiting | Add caching or reduce calls |
| Memory leak | Unbounded caching | Restart Data Service |
| Quality scores all 0 | No retrievals tracked | Verify tracking is enabled |

---

*Last Updated: December 2025*
*Version: Level 10 Memory System*

