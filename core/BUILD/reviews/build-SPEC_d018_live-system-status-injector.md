# AI Review — build/SPEC_d018_live-system-status-injector

**Verdict:** APPROVE · **Risk:** low

**Summary:** Read-only advisory status injector; fails closed, has kill switch, no money/secrets/prod-server mutation, scope narrower than spec and honestly disclosed.

## Findings
- No treasury/secrets/identity/main-branch touched; does not SSH or mutate servers 162/198/209 — only reads local repo mirrors and host load/disk. Spec asked for 'a service on 162' but impl is a repo-local read-only injector; this is narrower/safer and is honestly flagged in result+risks.
- Guardrail-preserving: keeps advisory disclaimer ('not approval to write/spend/deploy'), wraps all collection in try/except returning unchanged context (fails closed), and gates behind SH_LIVE_SYSTEM_STATUS_DISABLE=1. No silent bypass.
- PERF (non-blocking): _read_jsonl_tail reads the entire ops_ledger.jsonl into memory via read_text().splitlines()[-limit:] on every prompt build; an unbounded build ledger could make conversation-open slow. Consider a bounded tail read.
- MINOR (non-blocking): ops-ledger failure 'detail' (truncated to 160 chars) is surfaced into Ember's system prompt — low risk since it's self-context, but ledger entries are an uncontrolled text source. Acceptable given truncation.
- Behavior change: live status is now appended on BOTH the Supabase and repo-local context paths (previously Supabase returned early). Intended per spec; tests updated to assert the new 'Live system status:' / 'Build queue:' lines.
- render_status_lines caps total to max_items=6 while health can emit up to 5 lines plus 2 queue + 1 merge (=8), so the ops-ledger line may be dropped — bounded by design, not a defect.
- Tests added cover queue/merge/health, review fallback, and bounding; py_compile + diff-check clean. Registry row added as status=done (only Ember sets merged) — correct per SESSION_CONTRACT.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
