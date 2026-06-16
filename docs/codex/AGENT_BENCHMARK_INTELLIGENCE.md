# Agent Benchmarking Intelligence Layer

`tools/agent_benchmark_intelligence/engine.py` is the d057 advisory layer.

It has two halves:

- **Lantern:** normalizes externally collected AI benchmark findings, leaderboards, and eval-framework notes into dimension weights for `code_quality`, `critique_depth`, `learning_speed`, and `reasoning`.
- **Mirror:** scores repo-local agent evidence from `core/BUILD/REGISTRY.json`, build result files, and review markdown, then writes advisory placement recommendations.

Default runs are offline. Scheduled runs use `--live-public-sources`, which fetches a fixed allowlist of public benchmark/eval URLs and treats page text as data for dimension weighting only. External research can also arrive as a JSON/JSONL fixture or an explicit provider command that returns JSON and declares `cost_usd` under the cap. The tool does not run broad search, download models, train models, spend money, deploy, send outreach, or change routing authority.

Example:

```bash
python3 -B -m tools.agent_benchmark_intelligence.engine \
  --live-public-sources \
  --output core/BUILD/signals/agent_benchmark_intelligence.json \
  --append-ledger
```

The ledger path is `core/BUILD/signals/agent_scoring_ledger.jsonl`. Rows are one agent per run, schema `agent-scoring-ledger.v1`, and remain advisory until James/Ember approves a placement change.
