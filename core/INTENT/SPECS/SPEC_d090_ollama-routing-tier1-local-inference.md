# SPEC d090 — Ollama Routing: T1 Local Inference

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## What
Wire Ollama (9 models already running on 162 at localhost:11434) into the intelligence ladder as T1 — the cheapest sufficient carrier before escalating to claude -p.

## Why
T1 local inference was marked "future" but Ollama is live RIGHT NOW with llama3.1:8b, mistral:7b, qwen2.5-coder:7b, deepseek-coder:6.7b, phi3:mini and more. Every task routed locally saves tokens and increases sovereignty. Cost: $0.

## Deliverables

### `tools/intelligence/router.py`
- `route(task, context) → carrier` — picks T0/T1/T2/T3 based on task complexity
- T0: rule-based (routing, kill-switches, known patterns)
- T1: Ollama — low-complexity, high-volume tasks (contact research summaries, draft generation, classification)
- T2: GLM-5.2 or xAI (medium complexity)
- T3: claude -p / codex (complex builds, heavy review)

### `tools/intelligence/ollama_client.py`
- `generate(model, prompt, system=None) → str` — simple wrapper for Ollama REST
- `embed(text) → list[float]` — nomic-embed-text embeddings ($0)
- Model selection: phi3:mini for speed, llama3.1:8b for quality, qwen2.5-coder for code
- Fallback: if Ollama down, escalate to T3

### Tasks routed to T1 immediately
- contact pre-profiling summaries (d080)
- probe email draft generation (first pass)
- reply classification (is this a real reply or bounce?)
- council debate Pragmatist lens (replace with local where sufficient)

## Gates
- `OLLAMA_ROUTING_ENABLED=1` in curator.env (off by default, flip after proof)
- A/B log: T1 result vs T3 result for first 20 tasks — measure quality delta
- Never route to T1 for: build review, architecture decisions, James-facing comms

## Proof
- 10 contact summaries generated via llama3.1:8b, quality scored ≥ 3/5
- Cost comparison logged: T1=$0 vs T3 equivalent
