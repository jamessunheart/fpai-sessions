# Codex build result — SPEC_d018_live-system-status-injector
_ran: 2026-06-15T19:12:34Z · branch: build/SPEC_d018_live-system-status-injector_

## Summary
Built a read-only live system status injector for Ember owner-chat context. The existing `build_context_system_suffix()` path now prepends a bounded `Live system status` block on every chat prompt build, containing:

- current build queue counts and pending spec preview;
- active build/merge-request rows from `core/BUILD/REGISTRY.json`;
- last merge outcome from registry, with review/result fallback;
- local server health evidence: host id, repo readability, load, disk free, and ops-ledger failure summary when available.

The injector is advisory only and keeps the existing guardrail text: it does not approve writes, spend, deploy, send outreach, merge, restart services, or touch secrets. It fails closed behind `SH_LIVE_SYSTEM_STATUS_DISABLE=1`.

## Files changed
- `SERVICES/sunheart-brain/curator/live_system_status.py`
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/test_live_system_status.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/specs/SPEC_d018_live-system-status-injector.md`
- `core/BUILD/results/SPEC_d018_live-system-status-injector.result.md`
- `docs/codex/HANDOFF.md`

## Tests
- `python3 -B -m unittest SERVICES/sunheart-brain/curator/test_live_system_status.py SERVICES/sunheart-brain/curator/test_build_context.py SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py` — 9 tests OK.
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/live_system_status.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_live_system_status.py SERVICES/sunheart-brain/curator/test_build_context.py` — OK.
- `git diff --check -- SERVICES/sunheart-brain/curator/live_system_status.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_live_system_status.py SERVICES/sunheart-brain/curator/test_build_context.py core/BUILD/REGISTRY.json` — OK.
- Prompt smoke: direct `build_context_system_suffix(repo_root=Path("."), max_chars=1800)` rendered `Live system status` first with queue, active build, last merge, host, load, and disk lines.

## Risks
- This is repo/local-host evidence, not a live systemd probe. The sandbox did not SSH to server 162, deploy a unit, restart Telegram bot, or validate production credentials.
- Queue state depends on the registry/results/reviews mirrors being current.
- Host health is intentionally shallow and non-invasive: load, disk, repo readability, and optional ops-ledger rows.

## Rollback
Revert the changed files above. Immediate runtime kill switch: set `SH_LIVE_SYSTEM_STATUS_DISABLE=1` for the bot process to remove only the new status block while preserving the older build context/corrections injection.

## Intent solved
Ember owner-chat context now sees current build queue state, last merge outcome, and server health at conversation-open prompt assembly instead of requiring James to ask or remember the terminal state.

## Downstream intent unlocked
Ember can answer "what is happening on the build server right now?" from the same chat context and route the next merge/review/status move without James carrying Buildstream state manually.
