# 🧠 MEMORY ARCHITECTURE v1.0
## The Perfect System - Design Document

---

## Current State Analysis

### Existing Memory Systems

| System | Type | Scope | Persistence | Searchable |
|--------|------|-------|-------------|------------|
| **Mem0** | Cloud API | Long-term semantic | ✅ Permanent | ✅ Semantic |
| **ChromaDB** (AI Brain) | Vector DB | Embeddings | ✅ Local disk | ✅ Semantic |
| **SQLite** (Nerve Center) | Relational | Events, feeds | ✅ Local disk | ⚠️ SQL only |
| **Markdown Files** | File system | Knowledge docs | ✅ Git repo | ❌ Manual |
| **In-Memory** (Data Service) | RAM | Active items | ❌ Lost on restart | ⚠️ Filter only |

### Current Mem0 Contents
```
fpai_learnings: 1 memory (trading pattern)
fpai_insights: 0 memories
fpai_patterns: 0 memories
fpai_context: 0 memories
test_user_123: 1 memory (test)
```

### Current Markdown Knowledge
```
LEARNINGS.md: Trading system notes, parameters, backlog
PATTERNS.md: 12 architectural patterns
BEST_PRACTICES.md: 20 validated practices
FEEDS.md: External data sources
CONSCIOUS_FEEDS.md: Architecture integration
```

---

## The Problem

**Fragmented memory** = Lost wisdom

- Learnings in files not searchable by AI
- Patterns not connected to decisions
- No link between past outcomes and new situations
- Each session starts fresh

---

## The Solution: Unified Memory Graph

```
                    ┌─────────────────────────┐
                    │     MEMORY ROUTER       │
                    │    (Data Service)       │
                    └──────────┬──────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   HOT MEMORY    │  │  WARM MEMORY    │  │  COLD MEMORY    │
│   (In-Memory)   │  │    (Mem0)       │  │  (Markdown)     │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • Active items  │  │ • Learnings     │  │ • PATTERNS.md   │
│ • Current feed  │  │ • Insights      │  │ • PRACTICES.md  │
│ • Live metrics  │  │ • Decisions     │  │ • LEARNINGS.md  │
│                 │  │ • Outcomes      │  │ • Historical    │
│ TTL: Hours      │  │ TTL: Forever    │  │ TTL: Forever    │
│ Search: Filter  │  │ Search: Semantic│  │ Search: Manual  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Memory Types (Simplified)

### 1. LEARNINGS (What worked, what didn't)
```
user_id: fpai_learnings

Format: "{lesson}. Context: {context}. Action: {action}. Outcome: {outcome}."

Examples:
- "High funding rates precede corrections. Context: BTC funding >0.05%. Action: Reduced long. Outcome: Avoided 8% drawdown."
- "Deploy-first testing catches issues. Context: Dashboard release. Action: Tested deployment before code. Outcome: Zero production failures."
```

### 2. INSIGHTS (Synthesized intelligence)
```
user_id: fpai_insights

Format: "{title}: {content} (Category: {category})"

Examples:
- "AI Trend Alert: Multimodal models dominating December research. 15 arXiv papers on vision-language integration this week."
- "Market Signal: BTC OI divergence from price suggests incoming volatility."
```

### 3. DECISIONS (What we decided and why)
```
user_id: fpai_decisions

Format: "Decided: {decision}. Because: {reasoning}. Context: {market_state}. Expected: {expected_outcome}."

Examples:
- "Decided: Deploy sweep cycle trader. Because: Backtests show 2.3 Sharpe. Context: Low vol environment. Expected: $500/day profit."
```

### 4. OUTCOMES (What actually happened)
```
user_id: fpai_outcomes

Format: "Decision {decision_id} resulted in: {outcome}. Delta from expected: {delta}. Learning: {learning}."

Examples:
- "Decision deploy_sweep_001 resulted in: $320/day average. Delta from expected: -36%. Learning: Real slippage higher than backtest."
```

### 5. PATTERNS (Recurring structures)
```
user_id: fpai_patterns

Format: "Pattern: {name}. When: {condition}. Then: {effect}. Confidence: {confidence}%."

Examples:
- "Pattern: Funding Reversal. When: Funding >0.03% for 8+ hours. Then: Price corrects 3-8%. Confidence: 72%."
```

---

## Memory Flow Design

### WRITE Flow (Learning → Memory)
```
1. EVENT occurs (trade, decision, pattern detected)
         │
         ▼
2. DATA SERVICE captures
         │
         ▼
3. CLASSIFY memory type
         │
    ┌────┴────┐
    │         │
    ▼         ▼
4a. HOT     4b. WARM
(if active)  (if wisdom)
         │
         ▼
5. LINK to related memories (future enhancement)
```

### READ Flow (Context → Retrieval)
```
1. QUERY arrives ("What do we know about high funding?")
         │
         ▼
2. MEMORY ROUTER distributes
         │
    ┌────┼────┬────┐
    ▼    ▼    ▼    ▼
3. HOT  WARM COLD LIVE
   (ms) (sec) (read) (fetch)
         │
         ▼
4. MERGE & RANK results
         │
         ▼
5. RETURN unified context
```

---

## API Design

### Store Memories

```python
# Store a learning
POST /api/memory/learn
{
    "lesson": "High funding precedes corrections",
    "context": "BTC funding >0.05%",
    "action": "Reduced long exposure",
    "outcome": "Avoided 8% drawdown",
    "confidence": 0.8  # Optional
}

# Store a decision
POST /api/memory/decide
{
    "decision": "Deploy sweep cycle trader",
    "reasoning": "Backtests show 2.3 Sharpe",
    "context": {"market": "low_vol", "capital": 10000},
    "expected_outcome": "500/day profit"
}

# Store an outcome
POST /api/memory/outcome
{
    "decision_id": "dec_001",
    "actual_outcome": "320/day average",
    "delta": "-36%",
    "learning": "Real slippage higher"
}

# Store a pattern
POST /api/memory/pattern
{
    "name": "Funding Reversal",
    "condition": "Funding >0.03% for 8+ hours",
    "effect": "Price corrects 3-8%",
    "confidence": 0.72
}
```

### Retrieve Memory

```python
# Get context for a topic
GET /api/memory/context?topic=high+funding+rates
→ Returns: learnings, patterns, decisions, outcomes related to funding

# Search specific type
POST /api/memory/search
{
    "query": "market corrections",
    "types": ["learnings", "patterns"],
    "limit": 10
}

# Get decision context (before making decision)
GET /api/memory/decision-context?decision=open+long+position
→ Returns: Similar past decisions, outcomes, relevant patterns

# Get system wisdom (aggregated)
GET /api/memory/wisdom?topic=trading
→ Returns: Top patterns, best practices, key learnings
```

---

## Sync Strategy

### Markdown → Mem0 (Bootstrap)
```
1. Parse PATTERNS.md → Store as fpai_patterns
2. Parse LEARNINGS.md → Store as fpai_learnings
3. Parse BEST_PRACTICES.md → Store as fpai_insights
4. Run once to bootstrap, then live updates
```

### Mem0 → Markdown (Archive)
```
1. Weekly: Export high-value Mem0 memories
2. Append to appropriate .md files
3. Git commit for version control
4. Keep both in sync
```

---

## Implementation Priority

### Phase 1: Foundation (This Week)
- [x] Mem0 integration working
- [x] Basic store/search endpoints
- [ ] Simplified memory types (learnings, insights, patterns)
- [ ] Decision/Outcome tracking

### Phase 2: Bootstrap (Next Week)
- [ ] Parse existing .md files
- [ ] Bulk load to Mem0
- [ ] Deduplication logic
- [ ] Memory linking (relate memories)

### Phase 3: Intelligence (Week 3)
- [ ] Automatic pattern detection
- [ ] Decision → Outcome linking
- [ ] Confidence scoring
- [ ] Memory consolidation

### Phase 4: Integration (Week 4)
- [ ] AI Brain uses memory context
- [ ] Trading decisions query memory
- [ ] Dreaming Engine processes memories
- [ ] God Mode displays memory graph

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Memories stored | 2 | 100+ |
| Search relevance | 0.56 | 0.75+ |
| Context retrieval time | 900ms | 500ms |
| Decision context used | 0% | 80% |
| Learning capture rate | ~1/day | 10+/day |

---

## Memory Hygiene Rules

### What to Store
✅ Lessons that apply broadly
✅ Patterns that repeat
✅ Decisions with measurable outcomes
✅ Insights that change understanding

### What NOT to Store
❌ Raw data (keep in Data Service)
❌ Temporary state (keep in-memory)
❌ Duplicate information
❌ Low-confidence observations

### Cleanup Rules
- Remove memories with <3 retrievals after 90 days
- Consolidate similar memories weekly
- Archive outdated patterns monthly

---

## Next Action

**Bootstrap existing knowledge into Mem0:**

```bash
# Run bootstrap script (to be created)
python3 bootstrap_memory.py \
  --patterns core/INTELLIGENCE/PATTERNS.md \
  --learnings core/INTELLIGENCE/LEARNINGS.md \
  --practices core/INTELLIGENCE/BEST_PRACTICES.md
```

---

*Memory is intelligence compounding over time.*
*Design it well, and the system grows wiser every day.*

🧠💡✨















