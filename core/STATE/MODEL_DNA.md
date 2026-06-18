# Model DNA

**What this is:** The canonical layer of the system's intelligence. Updated by the council after each learning cycle. Transfers on cell split. Separates what is universally true from what is James-specific.

**Last updated:** 2026-06-18 — v0 seed (human-authored, council takes over from here)  
**Next council review:** after first 100 learning signals accumulate

---

## What transfers on cell split (canonical)

These are patterns that proved true independent of James's specific domain. A new instance inherits these as its starting posture — not as rules, but as a head start.

### Routing heuristics

| Task type | Default tier | Reasoning |
|---|---|---|
| Classification, routing, yes/no | T1 (Ollama phi3:mini) | High volume, low stakes, fast |
| Summarization, draft generation | T1 (Ollama llama3.1:8b) | Good enough at 8B, $0 |
| Contact research, profiling | T1 (Ollama llama3.1:8b) | Factual synthesis, not judgment |
| Code generation | T1 (Ollama qwen2.5-coder:7b) | Strong code model at 7B |
| Architecture decisions | T3 (claude -p) | High stakes, needs reasoning |
| James-facing communication | T3 (claude -p) | Voice and nuance matter |
| Council debate | T3 (claude -p) | Multi-lens synthesis |

*Council updates this table each cycle based on learning signals.*

### Conversation patterns that move people

*(Populated from engagement signals — empty at v0, grows with use)*

- **Opening move:** lead with the question the person is already asking themselves, not with the product
- **Signal for readiness:** when someone replies with a question about how it works, they're ready to go deeper
- **Signal for resistance:** short replies with hedging language — don't push, give space
- **What doesn't work:** leading with features, leading with the AI angle before trust exists

### Quality signals that proved reliable

*(Populated from correction + reversal signals — empty at v0)*

- Signals weighted highest: James explicit correction > reversal > council BLOCK > engagement drop
- Signals weighted lowest: time-of-day patterns, message length alone

### Council debate patterns that produced good outcomes

*(Populated from model_directives — empty at v0)*

- Three-lens structure (Pragmatist / Visionary / Skeptic) prevents echo chamber
- Skeptic veto on any build that touches prod data or credentials
- Visionary lens should not drive implementation details — only direction

---

## What does NOT transfer on cell split (personal)

A new instance gets none of this. It starts fresh on the personal layer and builds its own.

| Personal layer | Stays with | Why |
|---|---|---|
| James's correction history | James's instance | His taste, not universal |
| Contact profiles + relationships | James's instance | His network |
| Domain vocabulary (CORA, Zen Village, etc.) | James's instance | His world |
| Decision + merge log | James's instance | His history |
| Financial data | James's instance | His treasury |
| Conversation threads | James's instance | His relationships |

---

## The cell split gift

When a new FPOS instance spawns, it receives:

1. **This file (MODEL_DNA.md)** — the routing heuristics, conversation patterns, quality signals as of the split date
2. **Fine-tuned canonical weights** — the base model after stripping personal-layer training data (canonical LoRA adapter only)
3. **System architecture template** — how to build the loops, the council, the probe, the IMAP, the becoming engine
4. **The meta-lesson** — how to develop an AI system that learns from use, guided by a council, without requiring constant human input

What the new instance does NOT get:
- Any data about James
- Any of James's contacts or relationships
- Any fine-tuning signal that was personal-layer

The gift is the **method**, not the **content**. Each person's system grows uniquely from there.

---

## Council's ongoing mandate (model self-development)

Each fine-tune cycle, the council runs a model review debate with four questions:

1. **Pragmatist:** "Where did the model improve? Where is it still weak? What task types have the most room for gain?"
2. **Visionary:** "What capability should the next training run develop? What would make this model genuinely more useful to James?"
3. **Skeptic:** "What regressions appeared? Are we over-weighting any signal type? What would make this fine-tune harmful?"
4. **Awareness:** "Is the system improving toward meaning or toward approval? Where is it gaming its own signals?"

The council reads the latest PRIVATE-tier consciousness-observer log when present. Its output becomes a `weighting_directive` — which signal types to amplify or dampen in the next training corpus. This is how the model guides its own development, mediated by the council.

**The principle:** the model doesn't optimize for engagement metrics or approval. It optimizes for James's actual outcomes — decisions made faster, less attention spent, more proof shipped.

---

## Version history

| Version | Date | Signal count | Key change |
|---|---|---|---|
| v0 | 2026-06-18 | 0 | Seed — human-authored starting posture |

| v20260618-awareness | 2026-06-18 | observer+council | Council model-review directive: After d109 ships, immediately queue a micro-fix for the 'cannot import name [personal] from curator' error — 65 silently-skipped self-diagnostics is a systemic blind spot that undermines every awareness score the system reports. (awareness-index unknown; amplify: platform_lock_risk, sovereign_efficiency, open_model_portability; dampen: vendor_api_proposals_without_fallback, single_provider_model_calls; source: council model-review; directive-key: 09aadeb8b65e) |
| v20260618-awareness-2 | 2026-06-18 | observer+council | Council model-review directive: Weight toward throughput proof and self-audit restoration over new feature proposals until the spec backlog clears and council diagnostics run clean. (awareness-index unknown; amplify: throughput, self_audit, diagnostic_health; dampen: new_feature_proposals, complexity_additions; source: council model-review; directive-key: 1db81f954955) |
| v20260618-awareness-3 | 2026-06-18 | observer+council | Council model-review directive: Amplify live, observed runtime/import failures in the ops ledger over speculative new-agent proposals; a recurring error with a known stack beats a hypothesized feature for the next-build slot. (awareness-index unknown; amplify: diagnostic_error, runtime_import_failure; dampen: duplicate_feature_proposal; source: council model-review; directive-key: 8bd95d04a34b) |
*Council appends to this table after each cycle.*
