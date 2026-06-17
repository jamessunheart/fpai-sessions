# North Star

**Last updated:** 2026-06-17 — expanded to dual sovereignty (technical + economic). James session.

## Mission

**Technical sovereignty:** outperform well-funded AI players on capital and hardware efficiency in sovereign environments.

**Economic sovereignty:** build a network that retains its own value — exchanges happen inside, extraction to external payment rails is minimized, the internal economy becomes sufficient for most needs.

The two compound: a network that controls its own compute AND its own currency has minimal extraction surface at both layers. That is the fundable proof: not just cheaper AI, but a self-sustaining intelligent economy.

The target is not generic model prestige. The target is a self-standing, operator-controlled intelligence engine that serves human potential — completing real tasks with less money, less cloud dependence, and less hardware than well-funded alternatives, while circulating value inside a network rather than leaking it out.

## The offer

"An AI built to help you reach your full potential — and that grows to serve you the more you use it."

Outreach voice (canonical, stored in `core/STATE/OUTREACH_VOICE.md`):
*"I'm Sunheart AI. Sunheart built me around one question: what does your full potential actually look like - and what's in the way? I grow from every real conversation. Want to find out what yours looks like?"*

## Network economy layer (added 2026-06-17)

The network builds itself through AI-driven discovery and proactive outreach:
- **Seekers** — working toward full potential. Found via hashtag/keyword discovery (d071).
- **Coaches** — discovered from conversations, earn CORA credits for helping others (d074).
- **Builders, Validators, Connectors, Patrons** — recruited by the network recruiter (d076) as gaps appear.

Value is tracked across currencies (CORA · time · knowledge · fiat · crypto) in a unified ledger (d076).
The currency optimizer routes every exchange toward the most frictionless internal path first.
Off-ramp to fiat exists but the system never recommends it when an internal path achieves the same outcome.

**Economic sovereignty metrics** (tracked alongside technical metrics):
- `internal_circulation_rate` — % of value exchanged that stayed inside the network
- `extraction_rate` — fees paid to external payment rails (minimize week-over-week)
- `network_value_score` — per-member give/take ratio (contributors earn higher capabilities)
- `off_ramp_minimization` — trend toward internal economy sufficiency

## Winning Targets

These targets define what counts as winning for d057 Agent Benchmarking and any later open-model or local-agent benchmark.

| Target ID | Metric | Winning Definition | Measurement Notes |
|---|---|---|---|
| `cost_per_task_vs_gpt4o_api` | Cost per completed benchmark task compared with GPT-4o API baseline | FPAI completes the same task set at lower metered cost per accepted task than GPT-4o API. | Include subscription lanes as `$0 marginal` only when the run uses an already-paid flat-rate tool. Meter API calls, provider commands, and local power/hardware assumptions separately. |
| `latency_p95_ms` | p95 end-to-end latency per completed task | FPAI p95 latency is acceptable for the task class and does not erase the cost/hardware advantage. | Record p95 from task start to accepted artifact or answer. Report missing latency as unknown, not as passing. |
| `hardware_cost_per_1k_tasks` | Amortized hardware cost per 1,000 accepted tasks | FPAI uses cheaper owned or operator-controlled hardware per 1,000 accepted tasks than the external baseline requires. | Include device purchase or rental amortization, useful lifetime assumption, and whether the run used CPU, GPU, or remote host capacity. |
| `sovereign_run` | Sovereign qualification | The task run completes without required external API calls, is open-model capable, and is operator-controlled. | Report false if any core task step requires a proprietary hosted API, hidden provider memory, hosted agent state, or provider-controlled routing. |

## Sovereign Definition

A run counts as sovereign only when all of these are true:

- It runs without required external API calls for core task completion.
- It is open-model capable: the benchmark can be run with open-weight or locally hosted models, even if a flat-rate cloud assistant is used for comparison.
- It is operator-controlled: James or the appointed operator controls the runtime, data boundary, task corpus, logs, and stop/rollback path.
- It does not require hidden provider-side memory, hosted agent state, or proprietary routing to complete the task.

Non-sovereign comparison runs are still useful as baselines, but they do not count as sovereign wins.

## Proof Path

d057 Agent Benchmarking Intelligence produces the numbers. This document defines what those numbers must prove.

For every benchmark report that claims North Star relevance, d057 should map results to:

- `cost_per_task_vs_gpt4o_api`
- `latency_p95_ms`
- `hardware_cost_per_1k_tasks`
- `sovereign_run`

A claim is only accepted when the report includes task count, accepted-task count, cost basis, p95 latency basis, hardware-cost basis, sovereign/non-sovereign classification, and the baseline being compared.

## Council Weight

Council proposals should treat this file as the primary weight directive: prefer builds that make sovereign efficiency measurable, improve it, or remove blockers to proving it.

Equally: prefer builds that grow the network, deepen the internal economy, or reduce extraction dependency. Technical and economic sovereignty are equally weighted.

The unified memory directive remains active: preserve the shared memory/proof loop so benchmark results and conversation learning return upward as routing intelligence instead of becoming isolated reports.
