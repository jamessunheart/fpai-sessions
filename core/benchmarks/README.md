# Per-Agent Recursive Benchmarks

This directory stores the per-agent benchmark contract and the daily score time-series for d073.

`per_agent_scores.jsonl` is append-only. Each row is one agent on one run:

```json
{"agent":"forge","run_date":"2026-06-17","primary_metric":0.72,"metrics":{},"trigger_fired":false,"spec_queued":null}
```

On the first run, `tools/benchmarks/run_all_benchmarks.py` also writes `baseline_YYYY-MM-DD.json`. That baseline is Day 0 for the recursive-learning story: where each agent started, how its own metric moved, and which self-improvement specs were queued from drops or plateaus.

## Runner

Run manually:

```bash
python3 -B -m tools.benchmarks.run_all_benchmarks
```

Useful test/sandbox options:

```bash
BENCHMARKS_DISABLE=1 python3 -B -m tools.benchmarks.run_all_benchmarks
python3 -B -m tools.benchmarks.run_all_benchmarks --fixture /path/to/fixture.json --no-proposals
```

The runner isolates scorer errors, writes one JSONL score row per successful agent, logs `benchmark_run` rows to the ops ledger, and calls the proposal generator only for triggered agents.

When `BRAIN_INDEX_DSN` or `DATABASE_URL` is set and a Postgres driver is installed, the runner opportunistically reads bounded snapshots from `brain_index.probe_pool`, `probe_sessions`, `corrections`, `decisions`, and `council_debates`. Missing DB access is not fatal; the runner still scores repo-local registry, review, score-ledger, and ops-ledger evidence.

The reviewed systemd artifact enables `BENCHMARKS_PROPOSE_LIVE=1` and `BENCHMARKS_QUEUE_LIVE=1` so the live host can draft and queue triggered specs. Local manual runs remain dry by default unless those variables are set.

## Proposal Safety

`tools/benchmarks/improvement_proposer.py` is rate-limited to two queued specs per agent per week. In tests it accepts mocked `claude_runner` and `queue_build` callables. In normal sandbox/default use it does not call Claude unless `BENCHMARKS_PROPOSE_LIVE=1`, and it does not call `curator.decisions.queue_build()` unless `BENCHMARKS_QUEUE_LIVE=1`.

## Prompt Efficiency

`tools/prompt_efficiency/gepa_loop.py` tests prompt variants against synthetic fixture cases in `prompt_efficiency_cases.json`. For template-shaped prompts, it prefers the real MIT `gepa` package through `tools/prompt_efficiency/gepa_library.py`; if the package is unavailable or `GEPA_OPTIMIZE_DISABLE=1`, it falls back to deterministic candidates and records that status in the report. A variant is written to `prompt_efficiency_adoptions.json` only when quality is greater than or equal to baseline and average token count is lower. High-impact prompts such as council lenses are written to `pending_adoptions` until James/Ember approves active use. Current reports land in `core/BUILD/signals/prompt_efficiency.*` and `core/STATE/PROMPT_EFFICIENCY.md`.
