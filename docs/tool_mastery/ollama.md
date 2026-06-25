# ollama Mastery Card

## What it does best
Ollama is best for local, private, low-marginal-cost inference where latency, model size, prompt format, and hardware limits are explicit tradeoffs.

## Optimal use patterns (concrete, with examples)
- Match the local model to the job. Use smaller models for routing, extraction, classification, and drafts; reserve larger models for synthesis only when latency is acceptable.
- Keep prompts concise and structured. Local models degrade quickly when overloaded with irrelevant context.
- Prefer model-native chat templates through the Ollama API/CLI instead of hand-rolled role formatting when available.
- Cache stable context and keep repeated system text short.
- Measure latency and quality by task class; route hard or high-stakes work to stronger reviewed paths.

## Anti-patterns (what silently degrades it)
- Expecting cloud-frontier reasoning from a small local model.
- Loading huge context windows just because they fit.
- Using the wrong prompt format for the selected model family.
- Ignoring cold-start time, VRAM/RAM pressure, and concurrent request contention.
- Letting local fallback silently answer high-stakes tasks without a quality gate.

## Effort/parameter settings for this system
Use Ollama for low-risk local classification, extraction, and private drafts. Keep temperature low for routing/extraction. Track latency and fallback reasons in logs.

## Key constraints and hard limits
Local models are not a substitute for reserved decision authority, legal/financial review, or merge review. Hardware saturation can make the whole host feel broken, so concurrency needs a cap.

## How to detect it's not performing well
Latency spikes, outputs ignore schema, answers become generic, GPU/RAM pressure rises, or the same task succeeds under Claude/Codex but fails locally.

## Last updated + source
Seeded 2026-06-16 from Ollama local-model operating patterns and repo-local latency/cost discipline.

