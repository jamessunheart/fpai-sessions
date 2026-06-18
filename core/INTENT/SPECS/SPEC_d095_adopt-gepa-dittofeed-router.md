# SPEC d095 — Adopt GEPA + Dittofeed + vLLM Router (Forge Frontier Scan)

**Status:** queued | **Stream:** Game | **Blast radius:** additive, no removals

## What

Adopt three external projects found by Forge frontier scan that collapse multiple in-progress specs into simpler adoptions.

## GEPA — replaces primary fine-tune path in d093

**Repo:** github.com/gepa-ai/gepa (MIT, pip install gepa)

GEPA does reflective prompt evolution: takes corrections as natural-language feedback, evolves prompts automatically, 35x fewer iterations than LoRA, no GPU required. Runs through claude -p ($0).

**Change to d093:** GEPA becomes L2 (prompt evolution, $0). QLoRA fine-tune becomes L4 (only when GEPA plateaus). The `brain_index.corrections` table feeds GEPA directly — no dataset builder needed for the primary loop.

**Deliverable:** `tools/learning/gepa_evolver.py`
- Load corrections from brain_index.corrections
- Run GEPA evolution cycle against target task set
- Store evolved prompt variants in brain_index.model_directives
- A/B test evolved vs baseline, promote if improvement > 5%

## Dittofeed — replaces journey orchestration in probe + becoming engine

**Repo:** github.com/dittofeed/dittofeed (YC-backed, self-hostable, $0)

Self-hosted multi-channel journey engine: email + WhatsApp + SMS + Slack, git-versioned templates, branching on behavior signals. PII stays in our VPC.

**Change to d083/d092/d093 delivery:** Dittofeed owns journey orchestration (when to send, what channel, what branch). Our AI owns content generation. We stop hand-building state machines for "3-day follow-up → WhatsApp CTA → becoming nudge."

**Deliverable:** 
- Deploy Dittofeed as Docker container on 162 (alongside n8n)
- Wire probe_sessions → Dittofeed segment
- Define becoming-engine journey (spark→awaken→activate→build→contribute→coach stages)
- Connect Brevo (email), Evolution API (WhatsApp), Twilio (SMS) as Dittofeed channels

## vLLM Semantic Router — replaces hand-built T0→T5 dispatcher in d090

**Repo:** vllm-semantic-router.com (Red Hat-backed)

Routes per-request by cost/latency/privacy across local↔frontier. Config-driven, not code-driven. LiteLLM as OpenAI-compat proxy underneath.

**Change to d090:** Instead of building `tools/intelligence/router.py` from scratch, configure vLLM router + LiteLLM. Our routing logic becomes a YAML config file, not custom Python.

**Deliverable:**
- `pip install litellm` + configure as OpenAI-compat proxy in front of Ollama + claude -p
- Evaluate vLLM router as routing layer
- If too infra-heavy: fallback to RouteLLM (github.com/lm-sys/RouteLLM) — lighter alternative

## Also watch

- **LLMRouter** (github.com/ulab-uiuc/LLMRouter) — 16 trainable routers, lighter than vLLM
- **Self-evolving agent skill modules** — complement GEPA with reusable skill distillation for cell-split

## Gates
- All additive — evaluate before removing any existing build
- Dittofeed: deploy in shadow mode first, compare with existing probe loop
- GEPA: A/B against corrections table before promoting as primary path
- vLLM/LiteLLM: test with 10 routing decisions before replacing custom logic

## Proof
- GEPA produces measurable prompt improvement on at least 3 task types
- Dittofeed sends one becoming-engine email via its journey engine
- LiteLLM proxies successfully to both Ollama and claude -p
