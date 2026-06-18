# AI Review — build/SPEC_d073_per-agent-recursive-benchmarks-e

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds per-agent recursive benchmark scorers + daily runner + rate-limited improvement proposer; read-mostly, kill-switch present, queued specs still pass through build→review (no auto-merge), no money/secrets/main touched.

## Findings
- Committed service artifact ships BENCHMARKS_PROPOSE_LIVE=1 and BENCHMARKS_QUEUE_LIVE=1, so once the timer is installed the loop will auto-draft (claude -p) and auto-queue build specs unattended — this matches the spec intent and is gated (rate-limited 2/agent/week, proposals only enter the existing review gate, never auto-merge), and the branch does NOT install the timer; confirm Claude CLI + curator.decisions.queue_build availability on 162 before enabling, as the result already flags.
- brain_index reads on prod (162) are strictly SELECT/row_to_json with LIMIT 5000 and table names sourced from a hardcoded LIVE_TABLES tuple (no SQL injection); DB access is best-effort and non-fatal. Safe.
- Default manual runs append benchmark_run rows to the LIVE ops ledger (/opt/fpai-build/ops_ledger.jsonl) since that is the default path — this is additive/append-only and matches the spec ('Appends to ops_ledger'), but be aware ad-hoc local runs without --ops-ledger will write to the real ledger.
- forge_scorer first-pass-approve heuristic is loose: review files can contain both APPROVE and REQUEST_CHANGES, statuses[0] ordering is parse-order-dependent, and the `'REQUEST_CHANGES' not in statuses[:1]` check is redundant. This only affects a trigger metric (could fire/suppress a proposal), not a guardrail; low impact.
- proposer subprocess command is env-overridable via BENCHMARKS_CLAUDE_CMD (operator-controlled, not external input) with a 120s timeout and proposal prompt explicitly forbidding prod deploys/outreach/secrets/money/irreversible actions. Acceptable.
- run_all_benchmarks.py was truncated past the 60k cutoff — the visible portion (context build, baseline write, ops append, disable switch) is sound, but the tail (proposal dispatch loop, JSONL score writes) should get a quick manual eye before merge.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
