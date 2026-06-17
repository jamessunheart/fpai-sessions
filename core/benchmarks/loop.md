# Loop Benchmark

Primary metric: average `improvement_velocity`.

Metrics:
- `improvement_velocity`: week-over-week delta on each agent primary metric.
- `recursive_depth`: completed auto-queued improvement builds per agent.
- `north_star_cost_per_task`: ops-ledger cost rows divided by accepted build count.

Trigger: escalate to Council when any agent is flat for 14 days, defined as `abs(delta) < 0.02`.

