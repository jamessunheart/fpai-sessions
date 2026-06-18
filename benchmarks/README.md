# FPOS Public Benchmarks

This directory is the public-facing benchmark surface for FPOS.

## Methodology

- Source ledger: `core/benchmarks/per_agent_scores.jsonl`.
- Publication gate: an agent appears on the leaderboard only after at least 3 scored data points.
- Public fields: agent name, data-point count, latest run date, primary metric, delta from first scored point, and sovereign-run qualification.
- Private fields excluded: raw corrections, conversations, contacts, decision logs, treasury details, credentials, and personal DNA.

## Refresh

Run:

```bash
python3 tools/forge/public_benchmarks.py
```

The command writes `benchmarks/leaderboard.md` and a dated result snapshot under `benchmarks/results/`.

