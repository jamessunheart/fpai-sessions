# Steward Benchmark

Primary metric: `measurement_coverage`.

Metrics:
- `measurement_coverage`: unique ops-ledger event types seen divided by the known event manifest.
- `ledger_freshness_hours`: hours since the latest ops-ledger row.
- `correction_to_build_lag_hours`: median hours from correction captured to spec queued when IDs link both events.

Trigger: queue an instrumentation spec when `measurement_coverage < 0.8`.

