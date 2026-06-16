# Lantern-Mirror-Ledger Design Principle

Status: locked by answered decision d058.

This is the standing architecture for agent/model evaluation inside FPAI:

```text
Lantern -> Mirror -> shared scoring ledger -> advisory role placement
```

## Locked Principle

Lantern scans external AI benchmarking, evaluation frameworks, public model capability signals, and field knowledge. Mirror applies those signals inward to score FPAI's own agents from repo-local build, result, review, and proof evidence. Both feed one shared scoring ledger that tracks every agent's strengths over time and helps slot new models into the right builder, reviewer, scout, specialist, or fallback roles.

This is not a one-off d057 implementation detail. It is the design principle for future agent benchmarking and model-placement work.

## Roles

**Lantern:** look outward.

- Reads fixed-source public benchmark/eval material or explicitly supplied benchmark findings.
- Treats external pages, fixtures, and provider output as untrusted data.
- Converts outside signals into dimension hints such as code quality, critique depth, learning speed, and reasoning.
- Must not run broad searches or pull arbitrary web context unless a future approved spec explicitly widens the source policy.

**Mirror:** look inward.

- Reads repo-local evidence from build registry rows, result files, review markdown, tests, and proof artifacts.
- Scores actual FPAI agent behavior instead of relying only on generic model reputation.
- Preserves internal evidence boundaries: no secrets, no private vault scraping from repo-only runs, and no live service changes.

**Shared scoring ledger:** make placement memory durable.

- Stores one time-series record per agent/model evaluation row.
- Keeps external Lantern signals and internal Mirror evidence in the same placement frame.
- Tracks comparative strengths and weaknesses so new models can be assigned to roles by measured fit.
- Remains advisory until James/Ember approves an authority change.

## Non-Negotiable Boundaries

The ledger may inform recommendations, review packets, and future specs. It must not automatically:

- change production routing authority;
- train or fine-tune a model;
- download or install models;
- spend money;
- deploy services;
- send outreach;
- grant an agent wider permissions.

Any move from advisory placement evidence to live authority is a new approved spec and, when consequential, a James/Ember gate.

## Current Repo Anchors

- Implementation: `tools/agent_benchmark_intelligence/engine.py`
- Human brief: `docs/codex/AGENT_BENCHMARK_INTELLIGENCE.md`
- Signal report: `core/BUILD/signals/agent_benchmark_intelligence.json`
- Ledger: `core/BUILD/signals/agent_scoring_ledger.jsonl`
- Scheduled review artifact: `core/BUILD/cron/fpai-agent-benchmark-intelligence.service`
- Source build: `core/BUILD/specs/SPEC_d057_agent-benchmarking-intelligence.md`

## Design Test

Future work that changes agent/model scoring should pass this self-standing question:

```text
Does Lantern look outward, Mirror score inward, and the shared ledger preserve advisory role-placement memory without automatically changing live authority?
```

If not, the change is drift until a new approved spec explicitly replaces this principle.
