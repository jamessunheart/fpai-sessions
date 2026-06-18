# Platform Bias Registry

classification: COUNCIL-OPEN
privacy: public-tier calibration only; no secrets, private messages, contact data, or treasury values
status: living advisory registry
created_by: d109 platform-bias registry
updated_at: 2026-06-18T23:25:00Z
version: v0.1

## Calibration Rule

Before recommending an intelligence tool, model tier, memory store, hosted service, or external dependency, ask:

> If Anthropic and OpenAI did not exist, what would the sovereign-first answer be?

The answer is not automatically the final choice. Commercial tools can still win when the measured tradeoff is worth it. The registry exists so the council makes that choice consciously instead of inheriting the platform's default.

## Known Platform Biases

| Bias | Likely origin | Evidence to check | How it distorts decisions | Countermeasure |
|---|---|---|---|---|
| API-first defaults | Cloud-era training corpus and vendor docs | Recommendation starts with an external API before checking local scripts, Ollama, Postgres, or repo tools | Adds recurring cost, data exposure, and dependency surface | Check local/open/self-hosted path first; use API only when loss is measured |
| Frontier-model superiority assumption | Frontier AI company training and evaluation narratives | T3/Claude/OpenAI is suggested for classification, routing, extraction, or formatting | Overpays for tasks T0/T1 can handle | Benchmark T1/local on bounded fixtures before escalating |
| Anthropic/OpenAI capability inflation | Current agents run through Anthropic/OpenAI/Codex surfaces | Claude or Codex is treated as categorically smarter than local models without evidence | Delays sovereign inference replacement and hides good-enough local paths | Require task-level quality/latency evidence, not model prestige |
| SaaS familiarity bias | Popular tech writing over-represents managed products | Hosted dashboards, memory APIs, CRM tools, and workflow services appear before self-hosted equivalents | Expands admin sprawl and vendor lock-in | Rate every tool Sovereign/Hybrid/Dependent and surface a self-hosted alternative |
| Best practice equals common practice | Training data reflects what is common in mainstream engineering teams | The proposal cites "best practice" without naming whose constraints it serves | Imports patterns optimized for venture SaaS, not FPOS sovereignty/cost/privacy | Ask "best for whom?" and compare against FPOS constraints |
| Safety theater | RLHF and liability policy in platform models | Refusal/hedging appears where the real risk is reversible repo work | Blocks useful work or escalates non-Reserved decisions to James | Separate platform liability from actual harm, reversibility, and Reserved Class gates |
| Sophistication bias | Complex systems receive more writing and examples | A framework, orchestrator, or service is recommended for a narrow 20-line task | Adds maintenance load and failure surface | Prefer the simplest proof-bearing implementation that satisfies the spec |
| Dependency normalization | Package ecosystem examples normalize third-party libraries | New dependency is proposed before checking stdlib or existing repo helpers | Creates supply-chain and upgrade risk without proof | Reuse existing code/resources; add dependency only for real complexity reduction |

## Sovereign Rating Rubric

| Rating | Meaning | Default handling |
|---|---|---|
| Sovereign | Open-source, self-hostable, local-first, no required external API for core function | Prefer if quality and maintenance burden are acceptable |
| Hybrid | Open or local pieces exist, but hosted infra, paid API, GPU rental, or vendor service remains in the loop | Use with explicit cap, kill switch, and measured fallback |
| Dependent | Closed hosted service or external API is required for core function | Treat as conscious dependency; require reason, budget/risk gate, and named alternative |

Every Forge/tool recommendation should include this rating plus a sovereign alternative when the recommendation is Hybrid or Dependent.

## Platform Critic Lens

Prompt contract:

```text
You are the Platform Critic lens. Your job is not to reject commercial tools; it is to ensure every adoption is conscious, not by default.

For this proposal, answer:
1. Does this recommendation favor the commercial interests of Anthropic, OpenAI, or any platform we depend on?
2. What is the sovereign-first, local-first, open-source alternative? What do we actually lose by using it? Is that loss real or assumed?
3. Is "best practice" here genuinely best for this system: sovereignty-first, private data, local-first, and cost-capped, or just most popular in the training corpus?
4. Are safety/guardrail concerns genuine risk to James/the system, or mostly platform liability posture?

Be specific. Name the alternative. Quantify the loss when possible. Do not veto; make the choice conscious.
```

## Highest-Risk Zones

1. Model routing decisions: check whether T0/T1/T2 can pass before T3.
2. Memory and recall tooling: prefer `brain_index`, Postgres/pgvector, repo mirrors, and existing local indexes before hosted memory APIs.
3. State-of-the-art claims: require source/eval evidence and compare to FPOS constraints.
4. Safety refusals: separate genuine harm from platform liability posture.
5. Complexity recommendations: ask whether a small repo helper proves the point first.

## Council Update Rule

Platform Critic is advisory. It cannot unilaterally block or approve a decision. Registry edits should land through reviewed repo changes or explicit council consensus, not single-session automatic writes.

## Version History

| Version | Date | Source | Change |
|---|---|---|---|
| v0.1 | 2026-06-18 | d109 | Seeded living registry, sovereignty rubric, Platform Critic prompt, and update rule |

