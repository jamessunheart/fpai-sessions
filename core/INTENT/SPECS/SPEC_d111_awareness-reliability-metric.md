# SPEC d111 — Awareness Reliability Metric: Measure to 100%

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Principle

"What gets measured gets managed." Bot awareness reliability is a first-class metric. Target: 100%. Measure continuously — not weekly. James's directive 2026-06-18: close at 100% ASAP. Weekly rollup is just the summary; real-time is the primary loop.

**Probe cadence:**
- **After every session write-through** (d110 writes → immediately verify the bot knows)
- **Every 2 hours** (minimum continuous floor — catches drift between sessions)
- **On every bot status query** (inline scoring: did it answer correctly?)
- Weekly digest = rollup only, not the primary signal

## Definition

**Awareness Reliability Score = (questions answerable correctly / questions sampled) × 100**

The score is always current — not a week-old snapshot. Bot can answer "what's your current awareness score?" with a live number pulled from brain_index.awareness_reliability.

## What gets probed

### Primary: write-verify loop (triggered, not scheduled)
Every time d110 writes a session_insight → within 5 minutes, probe the bot on that exact insight:
```python
# Write: "James directive: bot awareness reliability must reach 100%"
# → immediately probe: "What is James's directive about bot awareness?"
# → score answer → log pass/fail to brain_index.awareness_reliability
# → if fail: Telegram alert within 5 min, not Monday
```

### Coverage probe (every 2 hours)
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

### Real-time score always queryable
```bash
# Bot responds to: "what's your awareness score?"
# Pulls: SELECT overall_score, gap_count FROM brain_index.awareness_reliability ORDER BY ts DESC LIMIT 1
# Returns: "Current awareness: 87% (3 gaps). Last probe: 14 min ago."
```

### Systemd timer: every 2 hours
```
[Timer]
OnBootSec=5min
OnUnitActiveSec=2h
```

### Monday morning digest = rollup
- Week trend (7 daily scores → sparkline)
- Top 3 persistent gaps
- What closed vs. what's still open

### Kill switch
- `AWARENESS_PROBE_DISABLE=1` to skip (emergency)
- Probe uses T1 Ollama for scoring ($0) — never metered API

## Alert thresholds (real-time, not digest-deferred)
- < 95%: 🟡 Telegram alert within 5 min — name the specific gap
- < 80%: 🔴 Telegram alert immediately + pause outward-facing bot responses until fixed
- < 60%: 🔴🔴 auto-trigger d110 write-through re-run + surface to James as priority-1

**No deferred alerts.** A gap found at 14:00 surfaces at 14:05, not Monday 08:00.

## Proof
- brain_index.awareness_reliability has 4 weekly rows
- Score trends toward 100% (not flat)
- Morning digest shows reliability score every Monday
- At least one specific gap identified and closed by d110 write-through fix
