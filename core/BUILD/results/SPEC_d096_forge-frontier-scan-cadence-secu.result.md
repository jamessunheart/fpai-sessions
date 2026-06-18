# SPEC_d096_forge-frontier-scan-cadence-secu Result

## Status

Done in working tree / awaiting merge review.

## Files Changed

- `tools/forge/frontier_scan.py`
- `tools/forge/daily_scan.py`
- `tools/forge/weekly_scan.py`
- `tools/forge/test_frontier_scan.py`
- `core/BUILD/cron/fpai-forge-daily.service`
- `core/BUILD/cron/fpai-forge-daily.timer`
- `core/BUILD/cron/fpai-forge-weekly.service`
- `core/BUILD/cron/fpai-forge-weekly.timer`
- `core/BUILD/activate/SPEC_d096_forge-frontier-scan-cadence-secu.sh`
- `core/BUILD/specs/SPEC_d096_forge-frontier-scan-cadence-secu.md`
- `core/BUILD/results/SPEC_d096_forge-frontier-scan-cadence-secu.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added the d096 Forge frontier scan cadence and security protocol as opt-in repo infrastructure. Daily and weekly scan commands use public-only prompts, run through `claude -p` by default, enforce 3-minute and 20-minute timeouts, parse structured findings, pass every write through the existing Forge security gate, and notify Telegram only when a public-safe quantum-leap finding crosses the configured threshold. Scans are disabled unless `FORGE_SCAN_ENABLED=1`; disabled-mode smoke checks return `skipped` without external calls.

Added reviewed systemd service/timer artifacts for 07:00 Athens daily and Monday 06:00 Athens weekly scans, plus an idempotent activation script for post-merge installation. The activation script was not run in this sandbox.

## Tests

- `python3 -B -m unittest tools.forge.test_frontier_scan tools.forge.test_frontier_node` (16 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/forge/frontier_scan.py tools/forge/daily_scan.py tools/forge/weekly_scan.py tools/forge/test_frontier_scan.py`
- `bash -n core/BUILD/activate/SPEC_d096_forge-frontier-scan-cadence-secu.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d096-registry.json`
- `FORGE_SCAN_ENABLED=0 python3 -m tools.forge.daily_scan --json`
- `FORGE_SCAN_ENABLED=0 python3 -m tools.forge.weekly_scan --json`
- `systemd-analyze calendar '*-*-* 07:00:00 Europe/Athens' 'Mon *-*-* 06:00:00 Europe/Athens'`
- `git diff --check`

## Commit

Attempted local `git add -A && git commit`; blocked because Git could not create `/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d096_forge-frontier-scan-cadence-secu/index.lock` on the read-only shared Git metadata.

## Risks

This branch proves parser, write-path, security-gate, disabled-mode, and timer-cadence behavior with offline tests. It does not prove seven live daily scans or one live weekly scan, because no external Claude/WebSearch scan, Telegram send, service install, deploy, push, merge, secret access, outreach, or money movement occurred in this sandbox. The security gate is conservative and pattern-based; human review remains required before public publication.

## Rollback

Revert the listed d096 files. If activation has run after merge, disable/remove `fpai-forge-daily.timer`, `fpai-forge-daily.service`, `fpai-forge-weekly.timer`, and `fpai-forge-weekly.service`, then run `systemctl daemon-reload`.

## Intent Solved

Forge frontier scans now have a scheduled, opt-in cadence and a permanent public/private write gate instead of ad hoc manual scanning.

## Downstream Intent Unlocked

Ember can enable the reviewed timers on the live host, observe seven daily scan rows plus one weekly report, and promote only public-safe ADOPT/WATCH findings into future specs.
