# Frontier Log

Rolling public-safe record of external frontier patterns that may improve FPOS.

Format:

`[date] [tier] [area] [project] [score] [action] [public note]`

## 2026-06-18

- [2026-06-18] [seed] [realtime-audio] [Pipecat] [score 8] [WATCH] Realtime audio orchestration remains useful for future public-lane adoption after local integration proof.
- [2026-06-18] [seed] [memory] [Cognee] [score 7] [WATCH] Graph memory patterns are relevant to the public template once private context stays fully separated.
- [2026-06-18] [seed] [learning] [GEPA] [score 8] [ADOPT] Prompt evolution can be described as a canonical public pattern using synthetic examples only.
- CONTRIBUTE: Pipecat - add a documented local transport fixture for sovereign-run tests - PR complexity: low
- CONTRIBUTE: Cognee - clarify rollback notes for graph schema migrations - PR complexity: med

## 2026-06-25 daily scan

- [redacted private/internal detail]
- [redacted private/internal detail]
- [2026-06-25] [daily] [council/multi-agent] [LangGraph (LangChain)] [score 7] [WATCH] Stateful graph-based agent orchestration; could replace ad-hoc council debate.py with typed state machines.
- [redacted private/internal detail]
- [2026-06-25] [daily] [routing/intelligence-ladder] [RouteLLM (LMSYS)] [score 9] [ADOPT] Learned binary router (strong vs weak model); directly implements T0–T5 intelligence ladder with cost savings.
- [2026-06-25] [daily] [local-model-inference] [llama.cpp + GGUF Q4_K_M] [score 8] [ADOPT] Proven T1 local inference on 162; Q4_K_M hits quality/speed sweet spot for rule-based routing tiers.
- [2026-06-25] [daily] [local-model-inference] [MLX (Apple Silicon) / llama.cpp server mode] [score 5] [SKIP] Apple-only; 162 is Linux x86. Not applicable for server fleet.
- [2026-06-25] [daily] [local-model-inference] [Tabby ML] [score 6] [WATCH] Self-hosted inference server with OpenAI-compatible API; Ollama alternative with better multi-model management.
- [2026-06-25] [daily] [multi-channel-messaging] [whatsapp-web.js / Baileys] [score 8] [WATCH] Unofficial WA bridge; proven in production by many HERMES-style projects; ToS risk but widely used.
- [redacted private/internal detail]
- [redacted private/internal detail]
- [2026-06-25] [daily] [becoming-engine/journey] [Zep (open-source memory)] [score 8] [WATCH] Session + long-term memory for LLM apps; self-hostable alternative to mem0 for champion journey state.
- [2026-06-25] [daily] [contact-discovery] [Composio (tool integrations)] [score 6] [WATCH] 200+ pre-built tool integrations for AI agents; enrichment + CRM actions without custom wiring.
- [2026-06-25] [daily] [cell-split/instance-templating] [Claude Code SDK (Anthropic)] [score 9] [ADOPT] Headless Claude Code via `claude -p` already in use; SDK enables programmatic multi-instance spawning for cell-split pattern.
- [redacted private/internal detail]

## 2026-06-29 daily scan

- [redacted private/internal detail]
- [2026-06-29] [daily] [routing] [RouteLLM / model-cascade routers] [score 9] [ADOPT] Learned router sends easy queries cheap, hard ones strong; exact fit for intelligence-ladder T0-T5.
- [2026-06-29] [daily] [learning] [DSPy (optimizer-driven prompt compilation)] [score 8] [WATCH] Programmatic prompt optimization; could systematize awareness-probe prompts against measured scores.
- [2026-06-29] [daily] [council] [AutoGen multi-agent debate orchestration] [score 8] [WATCH] Mature multi-agent conversation framework; could harden existing 3-lens council debate with role tooling.
- [2026-06-29] [daily] [messaging] [WAHA (WhatsApp HTTP API, self-hosted)] [score 8] [ADOPT] Self-hosted WhatsApp gateway enables HERMES multi-channel beyond Telegram at near-zero marginal cost.
- [redacted private/internal detail]
- [2026-06-29] [daily] [messaging] [Whisper.cpp + Piper TTS local voice] [score 7] [ADOPT] Fully local STT+TTS pipeline; removes metered voice API dependency for two-way voice on owned channels.
- [2026-06-29] [daily] [becoming] [Per-user stage-model LLM coaching patterns] [score 7] [WATCH] Spark-to-coach stage prompting implementable now atop existing becoming table; no new infra needed.
- [2026-06-29] [daily] [cell-split] [Parameterized agent instance spawning] [score 7] [WATCH] One spec spawns many parallel specialized instances; fits cell-split substrate growth pattern.
- [2026-06-29] [daily] [local] [vLLM high-throughput serving] [score 7] [WATCH] PagedAttention batching cuts self-hosted inference cost; relevant if local tier volume scales.
- [2026-06-29] [daily] [council] [LangGraph stateful agent graphs] [score 7] [WATCH] Graph-based orchestration with persistence; maps to decision-loop state machine but adds dependency weight.
- [2026-06-29] [daily] [enrichment] [Open-source contact enrichment scrapers] [score 6] [SKIP] Compliance and data-quality risk outweighs gains at current stage; revisit at scale.

## 2026-06-30 daily scan

- [2026-06-30] [daily] [routing] [RouteLLM] [score 9] [ADOPT] LMSYS router sends easy queries to cheap models, hard to strong — drops cost 50-80% with minimal quality loss.
- [2026-06-30] [daily] [learning / self-improvement] [DSPy] [score 8] [ADOPT] Stanford framework auto-compiles and optimizes prompt pipelines; replaces hand-tuned prompts with learned programs.
- [2026-06-30] [daily] [learning / self-improvement] [Unsloth] [score 8] [WATCH] 2-5x faster LoRA fine-tuning at 70% less VRAM; cheap on-device model specialization on a single GPU.
- [2026-06-30] [daily] [council / multi-agent] [CrewAI] [score 7] [WATCH] Role-based multi-agent orchestration with memory and tool use; closest public analog to the council-debate pattern.
- [2026-06-30] [daily] [contact discovery] [Exa AI] [score 8] [ADOPT] Semantic neural web search retrieves people and companies by meaning not keyword — direct enrichment primitive.
- [2026-06-30] [daily] [multi-channel messaging] [Cartesia Sonic] [score 7] [WATCH] Sub-100ms TTS with voice cloning; Twilio-compatible — viable voice layer for Telegram and WhatsApp channels.
- [2026-06-30] [daily] [local model inference] [llamafile] [score 7] [WATCH] Mozilla single-binary LLM runner; no install, CPU+GPU, cross-platform — zero-dependency local inference fallback.
- [2026-06-30] [daily] [becoming-engine / journey orchestration] [Temporal.io] [score 8] [WATCH] Durable workflow engine with retry and persistent state; maps cleanly to multi-month becoming journeys.

## 2026-07-01 daily scan

- [2026-07-01] [daily] [meta] [Forge daily scan] [score 10] [WATCH] WebSearch tool permission not granted in this run; scan could not query live sources today. Needs settings approval.

## 2026-07-03 daily scan

- [2026-07-03] [daily] [learning] [GEPA (reflective prompt evolution)] [score 8] [WATCH] Reflective prompt evolution fits our ladder self-improve loop; verify latest release live before adopting
- [redacted private/internal detail]
- [redacted private/internal detail]
