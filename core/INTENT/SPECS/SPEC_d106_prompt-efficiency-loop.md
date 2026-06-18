# SPEC d106 — Prompt Efficiency Loop

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Principle

Every prompt in the system is hand-written and never measured. If a prompt produces the same output quality in 40% fewer tokens, that is 40% more capacity within the same ceiling — no budget increase required.

Massive optimization across available constraints (per token, per second, per $0.01) is the growth lever. This spec owns the per-token dimension: output quality per token used.

## The compounding path

```
Better prompts → fewer tokens per run
    → more runs within $20/day ceiling
    → more signal generated
    → better learning → T1 handles more
    → T3 freed for harder problems
    → better outputs → more trust → more use
    → more signal → better prompts
```

The ceiling becomes irrelevant before you raise it.

## What gets measured

**For each system prompt (council lenses, forge scout, build review, morning digest, etc.):**

| Metric | How measured |
|---|---|
| Token count | input tokens + output tokens per run |
| Output quality score | council verdict (APPROVE/BLOCK/REVISE) as proxy; correction rate; human override rate |
| Signal density | useful decisions made per 1000 tokens consumed |
| Redundancy | % of input tokens that appear in zero output concepts |

**Efficiency score = output quality / tokens used**

Low score = prompt is long and noisy. High score = tight and precise.

## GEPA integration (Guided Evolutionary Prompt Adaptation)

For each underperforming prompt:
1. Run current prompt → measure baseline
2. Generate 3 compressed variants (shorter, same intent)
3. Run variants on same task type → compare quality score
4. Adopt winner if quality ≥ baseline at lower token count
5. Log: original tokens / new tokens / quality delta

No GPU required. $0 — runs on `claude -p` or T1 Ollama.

## Priority queue (biggest waste vectors first)

| Prompt | Estimated waste | Why |
|---|---|---|
| Council debate (3 lenses) | High | Runs every 5min, 3 calls, verbose system prompts |
| Build review (ai_review.py) | High | Full spec + context loaded every build |
| Morning digest generator | Medium | Synthesizes everything — prompt not tuned |
| Forge scout | Medium | New — hand-written, unmeasured |
| IMAP handler | Low | Runs 2min, but simple task |

## Deliverables

### `tools/efficiency/prompt_registry.yaml`
```yaml
prompts:
  - id: council_pragmatist
    path: tools/council/prompts/pragmatist.txt
    runs_per_day: ~288  # every 5min
    baseline_tokens: null  # measured on first run
    current_efficiency_score: null
    
  - id: build_review
    path: tools/build_loop/ai_review_prompt.txt
    runs_per_day: ~144  # every 10min
    baseline_tokens: null
    current_efficiency_score: null
```

### `tools/efficiency/measure_prompt.py`
- Runs a prompt N times on representative inputs
- Records: input tokens, output tokens, quality proxy score
- Writes to `brain_index.prompt_efficiency` table
- Baseline run on first measurement; comparison run after each GEPA iteration

### `tools/efficiency/gepa_optimize.py`
- Given a prompt ID with low efficiency score
- Generates 3 compressed variants via `claude -p`
- Tests variants against baseline inputs
- If winner found: proposes replacement (human-in-loop for high-impact prompts)
- Logs compression ratio + quality delta

### Weekly efficiency report (in Bandwidth Ledger)
- Top 3 prompts by token waste this week
- Top 3 prompts improved by GEPA this week
- Cumulative tokens saved since baseline
- Estimated capacity recovered: "Saved X tokens/day = Y equivalent council runs freed"

### Schema addition
```sql
CREATE TABLE prompt_efficiency (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    prompt_id TEXT,
    version INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    quality_score REAL,
    efficiency_score REAL,  -- quality / total_tokens
    gepa_iteration INTEGER DEFAULT 0
);
```

## Three-dimensional optimization (how d106 fits)

| Dimension | Spec | Mechanism |
|---|---|---|
| Per token | **d106 (this)** | Prompt efficiency loop — GEPA optimizes signal density |
| Per second | d104 Attention Engine | Context-triggered (not scheduled) = less idle compute |
| Per $0.01 | d105 Bandwidth Ledger | T1 graduation — routes cheap what can go cheap |

All three running together: same $20/day ceiling → exponentially more useful output.

## Gates
- High-impact prompt changes (council lenses, build review) require human approval before adoption
- Low-impact prompts (logging, formatting) auto-adopt if quality ≥ baseline
- GEPA runs on `claude -p` ($0 marginal)
- Measurement runs on T1 Ollama where possible
- Kill switch: `PROMPT_EFFICIENCY_DISABLE=1`

## Proof
- Baseline efficiency scores for top 5 system prompts
- At least 1 prompt improved by GEPA (compression ratio > 1.0, quality ≥ baseline)
- Cumulative tokens saved appears in weekly Bandwidth Report
- Council debate token usage trending down over 4 weeks
