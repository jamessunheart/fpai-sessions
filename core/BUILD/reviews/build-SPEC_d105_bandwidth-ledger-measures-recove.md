# AI Review — build/SPEC_d105_bandwidth-ledger-measures-recove

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds a private, best-effort bandwidth ledger (routing-decision JSONL + weekly T1-rate report + digest surfacing); contained, kill-switchable, no prod/money/identity/secret/main writes, DB write gated behind explicit env+DSN, first report honestly NO_DATA.

## Findings
- Hygiene: tools/router/route.py now appends to core/BUILD/signals/routing_log.jsonl on every route_once during the live autonomous build loop. This untracked, unbounded-growth file is NOT in .gitignore — it can be swept into autonomous build-loop commits or trip the parallel-session collision hook. Recommend adding signals/routing_log.jsonl to .gitignore.
- Minor: write_brain_index uses `with psycopg2.connect(dsn) as conn` which commits but does not close the connection (leak). Only triggers when BANDWIDTH_LEDGER_DB_WRITE=1, so not default-path; low impact.
- Semantic nit: bandwidth log status is appended to the RouteResult `skipped` list, conflating measurement status with skip reasons — cosmetic, no functional impact.
- Note (acceptable): recovered-capacity uses a hardcoded 20-min/T1 estimate; disclosed in report/risks and does not fabricate the WoW trend.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
