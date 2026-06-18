# AI Review — build/SPEC_d111_awareness-reliability-metric-con

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Awareness reliability probe (script + tests + uninstalled 2h timer + after-write hook wiring) — in-scope and well-tested, but wiring a synchronous prod-DB probe into the live continuity hook introduces a hang/latency risk and pollutes a live SSOT ledger.

## Findings
- append_session_hook.sh now runs reliability_probe.py synchronously on every successful session write; verify_latest() opens a brain_index DB connection with no visible timeout, so a slow/unreachable prod DB could block or noticeably delay the live continuity/settle hook (the --probe-latest path was never exercised against the real DB per the build's own risk notes).
- The probe appends an 'awareness_reliability_probe' event to the live SSOT ops ledger (/opt/fpai-build/ops_ledger.jsonl) on every write AND every 2h — high-frequency writes risk bloating the 'measured reality' ledger and skewing ops_log.py --summary semantics; confirm this event type is filtered out of existing summaries.
- write_reports() writes awareness_reliability.json/.md into the git working tree (core/BUILD/signals/) on every hook fire, producing persistent untracked/dirty files in a repo that has active parallel-session collision protection — consider a non-repo path or gitignore.
- reliability_probe.py uses top-level 'from verify_awareness import ...', which only resolves because the script dir lands on sys.path[0] under file-path invocation; this contradicts SESSION_CONTRACT Rule 6 (importlib-only cross-module imports) and would break if ever run as a module — tests already load it via importlib, masking the fragility.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
