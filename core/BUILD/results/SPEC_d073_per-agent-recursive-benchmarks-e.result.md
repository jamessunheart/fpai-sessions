# SPEC_d073_per-agent-recursive-benchmarks-e Result

Status: done / independently reviewed / awaiting merge review

## Summary

Added the d073 per-agent recursive benchmark layer. Beacon, Spark, Ember, Hermes, Council, Forge, Steward, and Loop now each expose a scorer with an agent-specific primary metric, metric payload, and trigger reason. The daily runner writes one JSONL row per agent to `core/benchmarks/per_agent_scores.jsonl`, creates a Day 0 `baseline_YYYY-MM-DD.json` on the first run, appends `benchmark_run` rows to the ops ledger, isolates scorer/proposal failures, and honors `BENCHMARKS_DISABLE=1`.

The runner can read fixtures for tests and bounded live snapshots from `brain_index` when `BRAIN_INDEX_DSN` or `DATABASE_URL` is present. The improvement proposer is rate-limited to two live queued specs per agent per week, includes the agent blueprint plus recent correction/revert context, and only calls Claude/`curator.decisions.queue_build()` when live env flags are set. The reviewed systemd artifact now runs the per-agent benchmark runner daily at 06:00 UTC with live proposal flags for the live host.

## Tests

- `python3 -B -m unittest tools.benchmarks.test_benchmarks` — 6 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/benchmarks/__init__.py tools/benchmarks/beacon_scorer.py tools/benchmarks/spark_scorer.py tools/benchmarks/ember_scorer.py tools/benchmarks/hermes_scorer.py tools/benchmarks/council_scorer.py tools/benchmarks/forge_scorer.py tools/benchmarks/steward_scorer.py tools/benchmarks/loop_scorer.py tools/benchmarks/improvement_proposer.py tools/benchmarks/run_all_benchmarks.py tools/benchmarks/test_benchmarks.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `BENCHMARKS_DISABLE=1 python3 -B -m tools.benchmarks.run_all_benchmarks --score-ledger /tmp/d073-disabled-scores.jsonl --ops-ledger /tmp/d073-disabled-ops.jsonl`
- fixture CLI smoke: `python3 -B -m tools.benchmarks.run_all_benchmarks --fixture /tmp/d073-fixture.json --score-ledger /tmp/d073-scores.jsonl --proposal-log /tmp/d073-proposals.jsonl --ops-ledger /tmp/d073-ops.jsonl --no-proposals`
- `git diff --check`

## Independent Review

Initial independent review found no P1 blockers and three P2 findings: registry closeout still marked building, Loop flatline trigger used 7-day semantics plus sample count instead of a 14-day flatline, and proposal prompts omitted recent correction/revert context. Fixes landed with regressions for Loop flatline and recent context. Final narrow re-review found no remaining P1/P2 blockers.

## Risks

This branch does not install the timer, call Claude, queue live specs, write to a live DB, push, or merge. Live proposal queueing depends on the live host having Claude CLI, `curator.decisions.queue_build`, and the correct DB/env configuration. The spec says "all 9 scorers" once, while its file list and per-agent definitions name eight agents; this implementation follows the explicit eight per-agent scorer files.

## Rollback

Revert the changed d073 files and remove the d073 registry/result/handoff entries. If the reviewed timer artifact is installed later, disable/remove `fpai-agent-benchmark-intelligence.timer` and restore the prior d057 service command if desired. Immediate runtime rollback is `BENCHMARKS_DISABLE=1`.

## Intent

Intent solved: each named agent now has a specific self-measurement loop instead of only generic d057 dimensions.

Downstream intent unlocked: the build loop can observe agent-specific drops or plateaus and route bounded improvement specs from measured weakness instead of manual noticing.
