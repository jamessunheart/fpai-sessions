# Ember Benchmark

Primary metric: `correction_rate` where lower is better.

Metrics:
- `correction_rate`: `brain_index.corrections` rows per day, measured as a rolling seven-day average.
- `memory_staleness_days`: days since `core/STATE/identity/ALIGNMENT.md` was modified.
- `session_start_coherence`: coherent `ops_ledger` session-start events divided by session-start events.

Trigger: queue a memory or behavior-pattern improvement spec when rolling `correction_rate > 3/day`.

