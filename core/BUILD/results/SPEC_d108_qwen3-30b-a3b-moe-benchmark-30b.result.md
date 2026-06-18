# SPEC_d108_qwen3-30b-a3b-moe-benchmark-30b Result

Status: done in working tree / awaiting merge review

## Summary

Added an offline-first benchmark harness for the d108 question: whether
`qwen3:30b-a3b` can match or beat `llama3.1:8b` quality while using a 3B-active
MoE compute profile.

The benchmark:

- builds an 8-task repo-local task pack from the existing open-model benchmark corpus;
- records candidate/baseline model profiles for `qwen3:30b-a3b` and `llama3.1:8b`;
- scores supplied JSONL responses for required terms, structure, evidence, latency, and quality per active parameter;
- declares the claim passed only when Qwen quality is greater than or equal to llama quality and Qwen active parameters remain at or below 3.5B;
- writes JSON and Markdown reports;
- supports bounded opt-in local Ollama execution without downloading models or changing routing.

No live Ollama run, model download, server SSH, production routing change,
deployment, push, merge, outreach, secret access, or money movement was
performed.

## Files Changed

- `tools/open_model_benchmark/qwen_moe_benchmark.py`
- `tools/open_model_benchmark/test_qwen_moe_benchmark.py`
- `core/BUILD/signals/qwen3_30b_a3b_benchmark.json`
- `core/STATE/QWEN3_30B_A3B_BENCHMARK.md`
- `core/benchmarks/README.md`
- `core/BUILD/specs/SPEC_d108_qwen3-30b-a3b-moe-benchmark-30b.md`
- `core/BUILD/results/SPEC_d108_qwen3-30b-a3b-moe-benchmark-30b.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.open_model_benchmark.test_qwen_moe_benchmark tools.open_model_benchmark.test_benchmark` -- 9 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/open_model_benchmark/qwen_moe_benchmark.py tools/open_model_benchmark/test_qwen_moe_benchmark.py tools/open_model_benchmark/benchmark.py tools/open_model_benchmark/test_benchmark.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -m json.tool core/BUILD/signals/qwen3_30b_a3b_benchmark.json`
- `python3 -B -m tools.open_model_benchmark.qwen_moe_benchmark --max-sources 8 --output core/BUILD/signals/qwen3_30b_a3b_benchmark.json --state core/STATE/QWEN3_30B_A3B_BENCHMARK.md`
- `git diff --check`

## Current Report

The generated report is in `task-pack` mode with 8 tasks. It does not claim a
live winner because this sandbox did not run Ollama or access server 162.

Live proof command for the approved target host:

```bash
python3 -B -m tools.open_model_benchmark.qwen_moe_benchmark --run-ollama --max-tasks 8 --output core/BUILD/signals/qwen3_30b_a3b_benchmark.json --state core/STATE/QWEN3_30B_A3B_BENCHMARK.md
```

## Risks

- The current branch proves the harness and task pack, not live Qwen quality.
- The default Ollama model tag is `qwen3:30b-a3b`; if the live host uses a
  different installed tag, Ember should adjust the profile or pass responses
  through JSONL rather than downloading a model from this harness.
- The scoring rubric is a deterministic repo-local proxy, useful for local
  replacement routing but not a public leaderboard claim.

## Rollback

Revert the files listed above and remove the d108 registry row. No live service,
model, or routing rollback is needed because nothing was activated.

## Intent Solved

Qwen3-30B-A3B now has a concrete benchmark harness against the local
`llama3.1:8b` baseline instead of an unmeasured model claim.

## Downstream Intent Unlocked

Ember can run one approved live Ollama pass on server 162 and use the resulting
quality/latency/active-compute comparison to decide whether Qwen3-30B-A3B should
be routed into local model replacement experiments.
