# AI Review — build/SPEC_d029_idle-triggered-self-audit-empty

**Verdict:** APPROVE · **Risk:** med

**Summary:** Local-only, proposal-only idle self-audit with kill switch, forbidden-class filter, 3-spec cap, and 24h limit; off feat/headless-build, no money/secret/main-branch writes.

## Findings
- GOOD: all signal collection is read-only (ops ledger, reviews, SELECT-only brain_index queries, systemctl status); no prod writes, no secrets, no main-branch touch. Branch correctly bases off feat/headless-build.
- GOOD: subprocess calls use list args (no shell=True), so spec/title text from the model cannot inject shell commands into `dec queue-build`. claude -p is $0 per cost policy.
- GOOD: defense-in-depth — kill switch SELF_AUDIT_DISABLE=1, MAX_SPECS cap of 3, 24h cap via .last_audit_date, FORBIDDEN_RE filtering money/treasury/identity/secret/prod-irreversible/delete/outreach, low/med risk only. Proposals are queued, not built directly; build+merge gates remain.
- MED RISK (self-amplification): this lets the autonomous loop author its own build specs and queue them via `dec queue-build`. The only content guard is a keyword regex (FORBIDDEN_RE) that a paraphrased spec could slip past. Bounded (1/24h, ≤3 specs) and still subject to the claude -p review + auto-merge gate, and James explicitly requested this behavior — but worth confirming queued self-audit specs are NOT tagged SAFE-AUTO so they surface to James rather than auto-build+auto-merge unsupervised.
- MINOR: .last_audit_date is stamped before the audit runs/succeeds, so a failed audit still consumes the 24h window (no retry until next day). Acceptable anti-thrash behavior but reduces coverage on transient claude -p failures.
- MINOR: merge_count trigger (>=10) is subordinate to the 24h cap, so it cannot fire more than once/day even under heavy merge volume — matches spec intent but means the counter can grow well past 10 before resetting.
- MINOR: spec referenced server_build_loop.sh but implementation modified build_orchestrator.sh; documented in result/handoff, not actual scope creep. Live paths (claude -p, dec, real ops_ledger, Telegram) were not exercised in sandbox — needs one live proof run as the handoff notes.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
