# SPEC d107 — Wire GEPA Library (Real Implementation of d106)

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## What

GEPA (Guided Evolutionary Prompt Adaptation) is not just a concept we coined — it's a shipping MIT-licensed library (ICLR 2026 Oral, arXiv 2507.19457). Wire it as the engine for d106 instead of building the optimizer machinery by hand.

**GitHub:** https://github.com/gepa-ai/gepa  
**DSPy integration:** https://dspy.ai/api/optimizers/GEPA/overview/

## Why it quantum leaps d106

- Pareto-frontier prompt evolution (mutate → eval → select winners) — fully built
- `optimize_anything` API: optimizes *any* text artifact — council lens prompts, forge scout prompts, morning digest template, not just task prompts
- Beats MIPROv2 by 13%, GRPO by 20%, using 35× fewer rollouts
- Reflection LLM → `claude -p` ($0 marginal)
- Eval rollouts → Ollama T1 ($0)
- 2-3 days to wire; replaces ~3 weeks of hand-built machinery in d106

## Integration plan

### 1. Install
```bash
pip install gepa  # or via DSPy: pip install dspy-ai
```

### 2. Wire reflection model → claude -p
```python
import gepa
# Reflection LLM: the one that diagnoses failures and proposes mutations
gepa.configure(reflection_model="claude-p")  # $0 marginal (subscription)
```

### 3. Define eval metric from our existing signals
```python
# Our metric: ops_ledger proof success rate + correction recurrence
# NOT a new eval — reuse what we already measure
def metric(prompt_output, expected):
    # Compare against corrections table (did this class of output get corrected?)
    # Compare against build review (APPROVE/BLOCK/REVISE)
    return quality_score  # 0.0 - 1.0
```

### 4. Run on highest-waste prompts first (per d106 priority queue)
```python
# 1. Council debate prompts (3 lenses, run ~288x/day)
optimized = gepa.optimize(
    prompt=council_pragmatist_prompt,
    metric=metric,
    trainset=recent_council_examples,  # from brain_index.decisions
    eval_model="ollama/llama3.1:8b"    # $0 rollouts
)
```

### 5. Adopt winners (gated)
- High-impact prompts (council, build review): propose to James before adopting
- Low-impact prompts (formatting, logging): auto-adopt if quality ≥ baseline
- Log all: original tokens / new tokens / quality delta

## What GEPA replaces from d106

d106 described building:
- Prompt variant generation → GEPA does this
- Pareto-frontier selection → GEPA does this  
- Quality measurement loop → GEPA does this

d106 still owns:
- `prompt_registry.yaml` (inventory of all system prompts)
- `brain_index.prompt_efficiency` table (our measurement log)
- Weekly efficiency report in Bandwidth Ledger

## Gates
- Reflection model: `claude -p` only (never metered Anthropic API)
- Eval rollouts: Ollama only (never metered)
- No prompt adopted without passing baseline quality check
- Human approval for council + build-review prompt changes
- Kill switch: `GEPA_OPTIMIZE_DISABLE=1`

## Proof
- GEPA installed and running on 162
- At least 1 council lens prompt optimized (compression ratio > 1.0, quality ≥ baseline)
- Tokens saved logged to `brain_index.prompt_efficiency`
- Bandwidth Ledger shows token reduction in council debate
