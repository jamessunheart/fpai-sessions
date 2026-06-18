# SPEC d105 — Bandwidth Ledger

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Principle

The system gains bandwidth by spending less of it on what it already knows how to do. But without measurement, the compound curve is invisible and therefore unsteerable.

The Bandwidth Ledger makes recovered capacity visible week over week. It is the metric that answers: "Is the system actually getting smarter about how it uses itself?"

## Three bandwidth vectors (from the architecture conversation)

| Vector | Mechanism | Proxy metric |
|---|---|---|
| **Compression** | Better memory organization → more signal per context load | Tokens loaded per decision vs. decision quality |
| **Tier graduation** | T1 learns what used to need T3 → T3 freed for harder work | T3 escalation rate per task type over time |
| **Parallel capacity** | Cell splits add network bandwidth; canonical layer improves all | (Phase 2 — not measurable until first cell split) |

## What gets measured

### Tier escalation rate (weekly)
```sql
-- How often did T1 handle the task vs. escalating to T3?
SELECT
  week,
  task_type,
  COUNT(*) FILTER (WHERE tier_used = 'T1') as t1_handled,
  COUNT(*) FILTER (WHERE tier_used = 'T3') as t3_escalated,
  ROUND(100.0 * COUNT(*) FILTER (WHERE tier_used = 'T1') / COUNT(*), 1) as t1_rate_pct
FROM routing_log
GROUP BY week, task_type
ORDER BY week DESC, task_type;
```
**Signal:** t1_rate_pct trending up = bandwidth recovered at T3

### Council debate rate vs. auto-resolved (weekly)
- How many intents reached council debate vs. were auto-resolved by rules/attention engine?
- Council debate = expensive bandwidth. Auto-resolve = bandwidth recovered.
- **Signal:** council debate rate trending down = attention engine + routing improving

### Correction recurrence rate (weekly)
- Did the same class of mistake recur this week that was corrected last week?
- Recurring corrections = bandwidth leak (spending T3 on known-bad patterns)
- **Signal:** recurrence rate trending to 0 = learning is landing

### Context load efficiency (per decision)
- Tokens loaded into context vs. tokens actually used in the decision
- High ratio = attention engine surfacing irrelevant content
- **Signal:** ratio trending toward 1.0 = attention engine improving

## Output: Weekly Bandwidth Report

```markdown
## Bandwidth Report — Week of {date}

### Recovered this week
- T1 handled {N}% of routing tasks (up {delta}% from last week)
- Council auto-resolved {N}% of intents (up {delta}%)
- Zero recurring corrections from last week's classes ✅ / {N} recurring ⚠️

### Bandwidth leaks
- Task types still escalating to T3 unnecessarily: [list]
- Recurring corrections: [list of classes]
- High context load / low utility decisions: [list]

### Compound curve
[sparkline: T1 rate over 8 weeks]
[sparkline: council auto-resolve rate over 8 weeks]
[sparkline: correction recurrence over 8 weeks]

### One sentence
"The system recovered {X} estimated T3-equivalent decisions this week by graduating them to T1."
```

## Deliverables

### `tools/bandwidth/routing_log.py`
- Logs every routing decision: task_type, tier_used, outcome (completed/escalated/failed), tokens_loaded
- Writes to `brain_index.routing_log` table
- Zero friction — called from existing routing paths

### `tools/bandwidth/weekly_report.py`
- Reads routing_log + council debate log + corrections table
- Produces Bandwidth Report
- Sends to morning digest on Mondays

### Schema addition to brain_index
```sql
CREATE TABLE routing_log (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    task_type TEXT,
    tier_used TEXT,  -- T1/T2/T3/T4/T5
    tier_intended TEXT,
    outcome TEXT,    -- completed/escalated/failed
    tokens_loaded INTEGER,
    tokens_used INTEGER,
    session_id TEXT
);
```

## Why this matters

Without this, the compound curve is invisible. We can say "the system gets smarter over time" but we can't see it happening, can't steer it, can't show it to funders, can't compare instance A to instance B.

With this, every week the report answers: **"Did we recover bandwidth this week, or did we leak it?"**

That's the fundable proof. Not "our AI gets smarter" — "our T1 escalation rate dropped 23% over 8 weeks, recovering estimated N hours of compute per week, compounding."

## Gates
- routing_log writes are non-blocking (log failures don't break routing)
- Runs entirely on T1 (Ollama) for report generation — $0 marginal
- Private tier — bandwidth data stays internal
- Kill switch: `BANDWIDTH_LEDGER_DISABLE=1`

## Proof
- routing_log table populated with 1 week of data
- Weekly report generated and sent to morning digest
- At least 1 task type shows measurable T1 rate improvement over baseline week
