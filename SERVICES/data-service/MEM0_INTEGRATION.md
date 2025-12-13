# 🧠 Mem0 Long-Term Memory Integration

The Data Service now has **persistent long-term memory** via Mem0.ai.

## Why Mem0?

Mem0 provides a memory layer that:
- **Persists insights** across restarts and sessions
- **Enables semantic search** over historical knowledge
- **Remembers patterns** and learnings over time
- **Builds organizational memory** that grows smarter

## What Gets Stored

### 1. **Insights** (`fpai_insights`)
High-value synthesized intelligence from data analysis:
- Research paper summaries
- Market analysis conclusions
- AI trend observations

### 2. **Patterns** (`fpai_patterns`)
Discovered trends and correlations:
- Category dominance patterns
- Trending topics
- Market correlations

### 3. **Learnings** (`fpai_learnings`)
What worked, what didn't:
- Successful trading patterns
- Strategy outcomes
- Decision retrospectives

### 4. **Context** (`fpai_context`)
System state snapshots:
- Decision context
- Market conditions at decision time

## Configuration

Set the Mem0 API key in your environment:

```bash
export MEM0_API_KEY="m0-your-api-key-here"
```

The service will:
- ✅ Work without the key (memory disabled, logging warning)
- ✅ Automatically enable when key is present
- ✅ Show status in `/health` endpoint

## API Endpoints

### Check Memory Status
```bash
GET /api/data/memory/status
```

### Search Memory
```bash
POST /api/data/memory/search
{
    "query": "market sentiment patterns",
    "type": "all",  # "insights", "patterns", "learnings", "all"
    "limit": 10
}
```

### Store a Learning
```bash
POST /api/data/memory/learn
{
    "context": "BTC funding rate exceeded 0.05%",
    "action": "Reduced long exposure",
    "outcome": "Avoided 8% drawdown",
    "lesson": "High funding often precedes corrections"
}
```

### Get Context for Topic
```bash
GET /api/data/memory/context/bitcoin%20liquidations
```

## Auto-Stored Memories

The following are stored automatically:

| Event | Memory Type | Trigger |
|-------|-------------|---------|
| Daily digest | Insight | Daily compression cycle |
| High-relevance analysis | Insight | Item with relevance > 0.7 |
| Pattern detection | Pattern | High-significance patterns |

## Usage by Other Services

### AI Brain
```python
# Get historical context before making decisions
context = await client.get("/api/data/memory/context/market_trends")
# Use context in prompt
```

### Strategic Intelligence
```python
# Search for relevant past learnings
learnings = await client.post("/api/data/memory/search", {
    "query": "successful trading strategies",
    "type": "learnings"
})
```

### God Mode
```javascript
// Display persistent insights in dashboard
const insights = await fetch('/api/data/memory/search', {
    method: 'POST',
    body: JSON.stringify({ query: "latest insights", type: "insights" })
});
```

## Monthly Allocation

- **$250/month** for 4 months
- Covers high-value memory storage
- Prioritizes insights over raw data

## Best Practices

1. **Quality over quantity**: Only store high-value insights
2. **Context is key**: Include rich context for learnings
3. **Search before decide**: Query memory before making decisions
4. **Learn from outcomes**: Store both successes and failures

---

*Memory is what makes intelligence grow over time.*















