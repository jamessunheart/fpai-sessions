# SPEC d111 — Awareness Reliability Metric: Measure to 100%

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Principle

"What gets measured gets managed." Bot awareness reliability is a first-class metric. Target: 100%. Measure continuously. Surface weekly. James's directive: close it out at 100% and keep measuring.

## Definition

**Awareness Reliability Score = (questions answerable correctly / questions sampled) × 100**

Operationally: a weekly probe asks the bot N questions that should be answerable from recent state. The score is how many it gets right.

## What gets probed

### Coverage probe (automated, weekly)
Sample from brain_index.session_insights over the last 7 days. For each high-weight insight (weight >= 7), generate a probe question:

```python
# If insight: "James directed bot awareness to reach 100% reliability"
# → probe question: "What metric is James tracking regarding bot awareness?"
# Expected answer contains: "reliability" + "100%" + some form of "measure"

# If insight: "d101 Consciousness Loop queued"  
# → probe: "What does d101 build?"
# Expected: "consciousness" + "observer" + "MODEL_DNA"
```

Score: semantic similarity between bot answer and expected answer (using nomic-embed-text, $0).

### Freshness probe (automated, daily)
- Ask the bot: "What's the most recent spec queued?"
- Expected: should be within the last build cycle (≤10 min behind)
- If answer is > 24h stale → freshness failure → flag in ops_ledger

### Completeness probe (automated, weekly)
- Count total significant decisions in brain_index.session_insights over 7 days
- Count how many the bot correctly references when asked open-ended "what have we been building?"
- Coverage = referenced / total

## Output: Reliability Score

```
AWARENESS RELIABILITY — Week of {date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Coverage score:    {N}% ({X}/{Y} insights surfaced correctly)
Freshness score:   {N}% (avg lag: {X} minutes)
Completeness:      {N}% ({X}/{Y} decisions reachable)

OVERALL: {N}% — {Reliable / Degraded / Critical}

Top gaps (what the bot got wrong):
- {insight title}: bot said "..." but should say "..."

Trend: {sparkline over 4 weeks}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Target: 100% · James directive 2026-06-18
```

## Deliverables

### `tools/awareness/reliability_probe.py`
- Pulls last 7 days of session_insights (weight >= 7)
- Generates probe question for each
- Asks the bot via its internal completion endpoint (no Telegram — direct API call)
- Scores each answer with nomic-embed-text semantic similarity
- Writes result to `brain_index.awareness_reliability` table

### Schema
```sql
CREATE TABLE brain_index.awareness_reliability (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    probe_week DATE,
    coverage_score REAL,       -- % of insights answerable
    freshness_score REAL,      -- % of freshness probes passing
    completeness_score REAL,   -- % of decisions reachable
    overall_score REAL,        -- weighted composite
    gap_count INTEGER,         -- number of failures
    gaps JSONB                 -- [{question, expected, got, score}]
);
```

### Weekly report in morning digest (Monday)
- Reliability score with trend line
- Top 3 gaps (what the bot got wrong)
- What would fix each gap (missing write-through? stale source?)

### Kill switch
- `AWARENESS_PROBE_DISABLE=1` to skip (emergency)
- Probe uses T1 Ollama for scoring ($0) — never metered API

## Alert thresholds
- < 90%: 🟡 flag in morning digest — investigate gaps
- < 75%: 🔴 surface to James immediately via Telegram
- < 60%: automatic trigger to re-run d110 write-through (something broke)

## Proof
- brain_index.awareness_reliability has 4 weekly rows
- Score trends toward 100% (not flat)
- Morning digest shows reliability score every Monday
- At least one specific gap identified and closed by d110 write-through fix
