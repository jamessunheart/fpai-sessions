# SPARK Shadow Graduation Rule

SPARK is a thin intake valve. It logs scorecard evidence only; it does not live-reroute, write memory, hold dialogue state, or make business decisions.

Promote a lane from shadow to live only after human review confirms all of the following over a named window of N days:

- high frequency: enough scorecard rows exist to show the lane is a real recurring path;
- high confidence: deterministic or llama-assisted confidence is consistently high;
- low risk: the lane has no money, people, public-send, production, secret, irreversible, or doctrine stakes;
- agreement: later `actual_outcome` / correction evidence agrees with `would_route`;
- rollback: live behavior can be disabled without data loss or service interruption.

Deterministic lanes may graduate first. Any stakes signal keeps the lane escalated, even when model confidence is low.
