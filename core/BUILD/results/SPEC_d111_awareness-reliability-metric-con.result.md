# SPEC_d111_awareness-reliability-metric-con Result

## Status
Done in working tree. Not pushed, merged, deployed, or installed.

## Files Changed
- `tools/awareness/reliability_probe.py`
- `tools/awareness/test_reliability_probe.py`
- `tools/continuity/append_session_hook.sh`
- `core/BUILD/cron/fpai-awareness-reliability.service`
- `core/BUILD/cron/fpai-awareness-reliability.timer`
- `core/BUILD/specs/SPEC_d111_awareness-reliability-metric-con.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary
Added a continuous awareness reliability probe that reuses `tools/awareness/verify_awareness.py`, appends every probe outcome to the ops ledger, writes JSON/Markdown metric reports, calculates rolling reliability, and alerts Telegram when the rolling score falls below 95%.

Added reviewed systemd artifacts for a two-hour cadence. Wired the existing session insight hook to run the same probe after a successful write path, with failures kept non-blocking for settle hooks.

## Tests
- `python3 -B -m unittest tools.awareness.test_reliability_probe tools.continuity.test_write_session_insights`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/awareness/reliability_probe.py tools/awareness/test_reliability_probe.py tools/awareness/verify_awareness.py tools/continuity/write_session_insights.py tools/continuity/test_write_session_insights.py`
- `bash -n tools/continuity/append_session_hook.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d111-registry.json`
- `git diff --check`

## Risks
- Live DB access was not available in this sandbox, so the real `--probe-latest` path was not executed against production `brain_index.session_insights`.
- The systemd timer is a reviewed artifact only; it was not installed or enabled.
- Telegram alerting depends on the existing `tools/build_loop/notify_telegram.sh` credentials and only records cooldown after that notifier reports `notify: sent`.

## Rollback
Revert the files listed above. If installed later, disable and remove `fpai-awareness-reliability.timer` and `fpai-awareness-reliability.service`.

## Intent Solved
Awareness visibility now has a measured reliability probe instead of a one-off manual verifier.

## Downstream Intent Unlocked
The live loop can alert James quickly when all-surface session awareness falls below the 95% reliability floor.
