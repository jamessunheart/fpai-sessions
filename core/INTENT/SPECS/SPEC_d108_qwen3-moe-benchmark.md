# SPEC d108 — Qwen3-30B-A3B MoE Local Model Benchmark

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## What

Pull `qwen3:30b-a3b` (Mixture of Experts) and benchmark against our current best T1 models on real tasks. Gate adoption on RAM headroom and tokens/sec under real load.

## Why it quantum leaps T1

**30B total parameters, only ~3.3B activate per token.** On a CPU-only server (162: 12 cores, 31GB RAM, ~20GB free, no GPU):
- Dense 30B model = impossible (too slow, too much RAM)
- Dense 8B model = current ceiling (llama3.1:8b)
- MoE 30B-A3B = ~30B-class reasoning quality at ~3B-class compute per token

This is a free quality upgrade at T1. No GPU. No cost. Just pull and benchmark.

## Benchmark protocol

### Step 1: RAM headroom check (before pull)
```bash
free -h  # confirm ~20GB free while Postgres + loops are running
# If < 18GB free: do not proceed (model Q4 ≈ 18-19GB)
```

### Step 2: Pull
```bash
ollama pull qwen3:30b-a3b     # Q4 quantized, ~18-19GB
ollama pull qwen3:4b          # replace phi3:mini / llama3.2:3b at the fast tier
```

### Step 3: Benchmark on our actual T1 task types
```bash
# Tasks we actually route to T1:
# - Contact classification (probe_pool scoring)
# - Draft summarization
# - Routing decisions (should this escalate?)
# - Code generation (small functions)

python3 tools/efficiency/benchmark_t1.py \
  --models llama3.1:8b qwen3:30b-a3b \
  --tasks classify summarize route code \
  --samples 20 \
  --metrics tokens_per_sec ram_peak output_quality
```

### Step 4: RAM under real load
```bash
# Run benchmark while build loop + council + IMAP poller are live
# If RAM spikes above 28GB (leaving < 3GB buffer): do not promote to default
watch -n 1 "free -h && cat /proc/meminfo | grep -E 'MemAvailable|SwapUsed'"
```

### Step 5: Promote or hold
- **Promote to default T1** if: quality ≥ llama3.1:8b AND tokens/sec ≥ 5 AND RAM < 28GB peak
- **Hold as optional heavy tier** if: quality better but tokens/sec < 5 (use only for longer reasoning tasks)
- **Skip** if: RAM pressure causes swapping (already at 4.7GB swap used)

## Also pull (fast tier replacement)
```bash
ollama pull qwen3:4b  # replaces phi3:mini for ultra-fast routing
# Benchmark same way — expected to be faster and better than phi3:mini
```

## Update RESOURCE_INVENTORY.md on completion
Add qwen3 models to the Local LLM table with measured tokens/sec and quality notes.

## Gates
- Do not pull if RAM headroom < 18GB (would cause swapping = worse than current)
- Benchmark runs DURING live load (not in isolation — real conditions)
- Do not change any routing config until benchmark shows clear win
- Rollback: `ollama rm qwen3:30b-a3b` (instant, no data lost)

## Proof
- Benchmark results logged comparing qwen3:30b-a3b vs llama3.1:8b on each T1 task type
- RAM peak measured under real load
- RESOURCE_INVENTORY.md updated with actual results
- Routing config updated only if benchmark shows clear quality win within RAM budget
