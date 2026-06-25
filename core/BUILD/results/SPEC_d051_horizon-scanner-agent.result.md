# SPEC_d051_horizon-scanner-agent · result

Status: done / awaiting James review + merge review

## Files changed

- `tools/horizon/__init__.py`
- `tools/horizon/scanner.py`
- `tools/horizon/horizon_config.json`
- `tools/horizon/test_scanner.py`
- `core/BUILD/cron/fpai-horizon-scanner.service`
- `core/BUILD/cron/fpai-horizon-scanner.timer`
- `core/BUILD/activate/SPEC_d051_horizon-scanner-agent.sh`
- `SERVICES/sunheart-brain/curator/jobs/digest.py`
- `core/BUILD/specs/SPEC_d051_horizon-scanner-agent.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d051_horizon-scanner-agent.result.md`
- `docs/codex/HANDOFF.md`

## Summary

Added the Horizon Scanner Agent. `tools/horizon/scanner.py` reads recent `brain_index` life/buildstream/interaction streams when a DSN is available, falls back safely when unavailable, reads ops-ledger and registry state, computes threshold signals, cross-correlates low energy with build load, composes one max-three-sentence Telegram surface, appends an ops-ledger `event=horizon_scan` row on every non-disabled run, and sends Telegram only when `signal=yes`.

Added `tools/horizon/horizon_config.json` with the requested thresholds, review-only systemd unit/timer artifacts for the 6h cadence, and an idempotent activation script to install/enable the timer after merge. The morning digest job now imports `recent_horizon_signal_lines()` and appends `⚡ Scanner flagged:` only for last-24h `signal=yes` horizon scan rows.

## Tests

- `python3 -B -m unittest tools.horizon.test_scanner` (12 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/horizon/scanner.py tools/horizon/test_scanner.py SERVICES/sunheart-brain/curator/jobs/digest.py`
- `python3 -m json.tool tools/horizon/horizon_config.json`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `bash -n core/BUILD/activate/SPEC_d051_horizon-scanner-agent.sh`
- `python3 -B tools/horizon/scanner.py --ops-ledger /tmp/fpai-horizon-smoke-no-claude.jsonl --disable-file /tmp/fpai-horizon-disabled-smoke --no-send --no-claude --json`
- `git diff --check -- tools/horizon SERVICES/sunheart-brain/curator/jobs/digest.py core/BUILD/cron/fpai-horizon-scanner.service core/BUILD/cron/fpai-horizon-scanner.timer core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d051_horizon-scanner-agent.md`

## Independent review

Completed by review-only subagent. It found six issues: timer cadence skipped midnight, curator digest might not import repo `tools`, notifier skip could be recorded as sent, empty interaction streams missed silence, proposal drought was missing, and registry was still building. Fixed all six at the time, then this closeout pass aligned the timer with the spec's requested `OnCalendar=*-*-* 06/6:00:00 UTC`, added the missing activation script, and added the missing registry row. Digest import uses explicit `importlib` loading from `FPAI_CODEX_REPO`/`/opt/fpai-build/FPAI_Cockpit`; Telegram sent requires notifier stdout to include `sent`; complete silence is detected when the interaction source is available; proposal drought is implemented.

Fresh independent review of the closeout delta was attempted with local Claude CLI and failed in this sandbox with `API Error: Unable to connect to API (ConnectionRefused)`. Rerun independent review from the live/writable host before merge if the merge gate requires current review coverage for the activation/timer/registry delta.

## Commit status

Blocked in this sandbox. `git commit -m "Add horizon scanner agent"` failed because Git could not create `/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d051_horizon-scanner-agent/index.lock`: read-only file system.

## Risks

Live `brain_index` schema, live `claude -p`, real Telegram send, and timer activation were not exercised in this sandbox. The scanner uses dynamic table-column discovery and safe empty-stream fallback, but live signal quality still depends on d045 life-event field names being populated consistently. The systemd files and activation script are review-only artifacts and were not installed.

## Rollback

Delete `tools/horizon/`, `core/BUILD/cron/fpai-horizon-scanner.service`, `core/BUILD/cron/fpai-horizon-scanner.timer`, `core/BUILD/activate/SPEC_d051_horizon-scanner-agent.sh`, and this result file; revert the additive morning digest import/section in `SERVICES/sunheart-brain/curator/jobs/digest.py`; remove the d051 registry row and HANDOFF note. If installed later, disable/remove `fpai-horizon-scanner.timer` and `fpai-horizon-scanner.service`, then run `systemctl daemon-reload`. Runtime kill switches are `HORIZON_DISABLE=1` or `/opt/fpai-build/.horizon_disabled`.

## Intent solved

Life/buildstream/interaction signals can surface predictive pattern warnings before James has to notice them manually.

## Downstream intent unlocked

d045 Life Data Intake can produce actionable early-warning surfaces instead of becoming another inbox, while morning digest remains a digest and Horizon remains silent unless a threshold crosses.
