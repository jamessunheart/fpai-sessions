# Council Benchmark

Primary metric: `build_success_rate`.

Metrics:
- `proposal_build_rate`: council decisions with `build_status` built/done/merged divided by council proposals.
- `build_approve_rate`: approved reviews divided by council proposal builds.
- `build_success_rate`: `proposal_build_rate * build_approve_rate`.
- `convergence_rate`: all-lens convergence debates divided by total debates.

Trigger: queue a council self-diagnostic spec when `build_success_rate < 0.6`.

