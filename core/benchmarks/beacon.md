# Beacon Benchmark

Primary metric: `source_quality`.

Metrics:
- `discovery_rate`: `probe_pool` rows added per day from `created_at`.
- `source_quality`: engaged `probe_sessions` divided by `probe_pool` contacts per source.
- `signal_precision`: discovered contacts with `discovery_score >= 0.7` divided by discovered contacts.

Trigger: queue a source-improvement spec when `source_quality < 0.4` for any source with at least 10 contacts.

