# AI Review — build/SPEC_d117_post-merge-liveness-probe-auto-d

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Read-only post-merge liveness probe (systemd/table/file/endpoint/port) with kill-switch and external-endpoint gating; safe and in-scope, but a double-logging bug collapses 'partial' into 'dead' in two of the three honest-map surfaces — contradicting the feature's own purpose.

## Findings
- Double-log / status mismatch: probe.py already appends its own honest ops-ledger row (e.g. event=liveness:partial, liveness_status=partial), then server_build_loop.sh sees probe exit code 1 for partial/dead and appends a SECOND row hardcoded as event 'liveness:fail' (no liveness_status). Because live_system_status._liveness_summary and liveness_status.liveness_honest_map_lines both take the LATEST row per spec_id, the shell's later liveness:fail row overrides the probe's liveness:partial → a PARTIAL build is reported as DEAD in the digest and live-system map. This directly defeats the spec's 'honest live/partial/dead/planned' goal. Fix: pass --no-ledger from the shell (let probe.py be the sole writer) or have the shell derive the event from the probe's printed status instead of forcing liveness:fail.
- Minor: tools/liveness/probe.py hardcodes a default DB_URL with credential 'postgres://brain_index:changeme@127.0.0.1:25432/appflowy'. Local-only and env-overridable, but avoid shipping an embedded default password — fall back to empty/raise if BRAIN_INDEX_DB_URL is unset.
- Note (pre-existing, low risk): _check_command still executes arbitrary shell via bash -lc from the legacy liveness_check field. Acceptable as d115 back-compat since input originates from the trusted decisions table, but new specs should use typed declarations and the legacy path should be deprecated as stated.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
