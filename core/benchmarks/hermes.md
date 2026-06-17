# Hermes Benchmark

Primary metric: `response_rate` per channel.

Metrics:
- `delivery_rate`: sent `probe_sessions` divided by contacted `probe_pool` rows.
- `response_rate`: engaged sent sessions divided by sent sessions per platform.
- `channel_efficiency`: response rate divided by estimated cost per send.

Trigger: queue a channel-improvement spec when `response_rate < 0.2` for any channel with at least 20 sends.

