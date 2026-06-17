# Spark Benchmark

Primary metric: `routing_completion`.

Metrics:
- `routing_completion`: `probe_sessions.completed_spark = true` divided by sessions.
- `drop_off_message`: median message number where conversations end.
- `conversation_continue_rate`: sessions reaching message 3 or later divided by sessions.

Trigger: queue a Spark-opening improvement spec when median `drop_off_message < 3`.

