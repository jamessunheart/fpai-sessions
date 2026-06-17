# Forge Benchmark

Primary metric: `first_pass_approve_rate`.

Metrics:
- `first_pass_approve_rate`: first-review approvals divided by reviewed builds with no first-pass request-changes.
- `revert_rate`: auto-reverted or reversed merges divided by merges from the ops ledger.
- `cycle_time_hours`: median hours from spec-written/start timestamp to done/merged timestamp when available.

Trigger: queue a build-loop/session-contract strengthening spec when rolling `first_pass_approve_rate < 0.6`.

