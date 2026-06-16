# SPEC_d057_agent-benchmarking-intelligence Result

Status: done / independently reviewed / awaiting merge review

## Summary

Added the d057 Agent Benchmarking Intelligence layer. It combines:

- Lantern: fixed-source public benchmark/eval scanning, fixture ingestion, and explicit JSON provider ingestion for external benchmark findings.
- Mirror: repo-local scoring from build registry rows, result files, and review markdown.
- Shared ledger: `agent-scoring-ledger.v1` JSONL rows with dimensions for `code_quality`, `critique_depth`, `learning_speed`, and `reasoning`.
- Placement recommendations: advisory-only role suggestions with hard gates against production routing, training, spending, deployment, or outreach changes.

The scheduled artifact runs every 6 hours with `--live-public-sources --append-ledger`. Live scanning is limited to a fixed URL allowlist and falls back to seed findings with warning evidence if public fetches fail.

## Files Changed

- `tools/agent_benchmark_intelligence/__init__.py`
- `tools/agent_benchmark_intelligence/engine.py`
- `tools/agent_benchmark_intelligence/test_engine.py`
- `docs/codex/AGENT_BENCHMARK_INTELLIGENCE.md`
- `core/BUILD/cron/fpai-agent-benchmark-intelligence.service`
- `core/BUILD/cron/fpai-agent-benchmark-intelligence.timer`
- `core/BUILD/signals/agent_benchmark_intelligence.json`
- `core/BUILD/signals/agent_scoring_ledger.jsonl`
- `core/BUILD/specs/SPEC_d057_agent-benchmarking-intelligence.md`
- `core/BUILD/results/SPEC_d057_agent-benchmarking-intelligence.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.agent_benchmark_intelligence.test_engine` -- 8 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/agent_benchmark_intelligence/engine.py tools/agent_benchmark_intelligence/test_engine.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -m json.tool core/BUILD/signals/agent_benchmark_intelligence.json`
- `git diff --check`
- CLI smoke: `python3 -B -m tools.agent_benchmark_intelligence.engine --output /tmp/d057-agent-benchmark-intelligence-live.json --ledger /tmp/d057-agent-scoring-ledger-live.jsonl --append-ledger --live-public-sources`

## Independent Review

Independent AI review first found three issues:

- registry/result still marked `building`;
- timer reused only seed findings instead of live external sources;
- provider command used `shell=True`.

Fixes applied:

- registry/result now mark the build done;
- scheduled service now runs `--live-public-sources`;
- live source scan fetches only a fixed public benchmark allowlist and falls back with warning evidence;
- provider command execution now uses `shlex.split(...)` and `shell=False`;
- tests cover fixed-source live fetch, partial failure reporting, and total failure fallback.

Final re-review reported no remaining blockers.

## Risks

- Public benchmark pages are fetched as untrusted data only. Page structure changes can reduce dimension inference quality.
- If the host has no outbound network, the scheduled scan falls back to seed findings and records warning evidence.
- Scores are heuristic/advisory; they should inform review and placement discussion, not automatically change model routing or authority.
- The provider command path still depends on an explicitly configured local command; it is safer than shell execution but should remain review-gated.

## Rollback

Revert the files above and remove the d057 entry from `core/BUILD/REGISTRY.json`. If Ember installs the timer later, disable/remove `fpai-agent-benchmark-intelligence.timer` and `fpai-agent-benchmark-intelligence.service`, then run `systemctl daemon-reload`.

## Intent Solved

Agent/model placement can now be scored from current external benchmark signals and internal build/review evidence instead of relying on generic model reputation.

## Downstream Intent Unlocked

Ember/James can review the first time-series agent scoring ledger, compare Codex builder vs independent reviewer capability trends, and route future model-placement specs from measured evidence.
