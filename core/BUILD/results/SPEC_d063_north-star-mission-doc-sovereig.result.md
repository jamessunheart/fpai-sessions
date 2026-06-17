# SPEC_d063_north-star-mission-doc-sovereig Result

## Status

Done / independently AI-reviewed / awaiting merge review.

## Summary

Created `core/STATE/NORTH_STAR.md` as the machine-readable sovereign benchmark target. It defines the mission, measurable target IDs, sovereign-run criteria, and the proof path where d057 Agent Benchmarking Intelligence produces the numbers.

Patched `core/STATE/COUNCIL_FOCUS.md` so council debate treats `NORTH_STAR.md` as a primary weight directive alongside the unified memory directive.

Updated d057 Agent Benchmarking Intelligence so generated reports include a `north_star` block with the target IDs and criteria:

- `cost_per_task_vs_gpt4o_api`
- `latency_p95_ms`
- `hardware_cost_per_1k_tasks`
- `sovereign_run`

## Tests

- `python3 -B -m unittest tools.agent_benchmark_intelligence.test_north_star tools.agent_benchmark_intelligence.test_engine` — 11 tests OK.
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/agent_benchmark_intelligence/engine.py tools/agent_benchmark_intelligence/test_north_star.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d063-registry.json`
- `python3 -B -m tools.agent_benchmark_intelligence.engine --output /tmp/d063-agent-benchmark.json --json`
- `git diff --check`

## Independent Review

Read-only AI review found:

1. Registry still marked `building` before closeout.
2. `sovereign_run` initially mapped only to a proof-path bullet instead of the actual sovereign criteria.

Fixes applied:

- Added `sovereign_run` to the North Star target table with explicit sovereign criteria.
- Strengthened `tools.agent_benchmark_intelligence.test_north_star` to require external-API, open-model, and operator-controlled criteria in d057 JSON.
- Registry is marked done after passing validation.

## Risks

This defines the target and report mapping; it does not yet produce live benchmark numbers, run local models, buy hardware, change routing authority, deploy, spend, or call external APIs. The next live d057 benchmark still needs measured task counts, accepted-task counts, cost basis, latency basis, hardware-cost basis, sovereign classification, and comparison baseline.

## Rollback

Revert `core/STATE/NORTH_STAR.md`, the `COUNCIL_FOCUS.md` addition, the d057 `north_star` report mapping, `test_north_star.py`, the documentation note, this result file, the d063 spec artifact, the d063 registry row, and the d063 handoff entry.

## Intent solved

The North Star benchmark target is now repo-readable and machine-addressable instead of living only in chat.

## Downstream intent unlocked

d057 benchmark output and the next council debate can cite the same sovereign efficiency targets, making "winning" measurable for funding narrative, local/open-model replacement work, and build-loop prioritization.
