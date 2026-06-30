# SPEC_f57b8fb5-4b47-4a3d-aa59-9a1d4ea89a46_daily-value-check-did-the-system

Status: done in working tree / awaiting merge review

## Summary

Added a daily value check feedback loop. A systemd timer runs at 20:00 Europe/Athens and sends James the fixed Telegram prompt:

> Did I help you today? What would have helped more?

The prompt runner records an awaiting state in `/var/lib/sh-brain/daily_value_check.json`. The private owner Telegram handler consumes the next ordinary one-line reply, appends it to `brain_index.corrections` with `source='daily_value_check'`, marks the state captured, and acknowledges without running the normal chat-answer path.

Rollback is `touch /opt/fpai-build/.daily_value_check_disabled`. The activation script installs/enables the reviewed service/timer after merge.

## Files Changed

- `SERVICES/sunheart-brain/curator/daily_value_check.py`
- `SERVICES/sunheart-brain/curator/test_daily_value_check.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`
- `SERVICES/sunheart-brain/index/schema.sql`
- `core/BUILD/cron/fpai-daily-value-check.service`
- `core/BUILD/cron/fpai-daily-value-check.timer`
- `core/BUILD/activate/SPEC_f57b8fb5-4b47-4a3d-aa59-9a1d4ea89a46_daily-value-check-did-the-system.sh`
- `core/BUILD/specs/SPEC_f57b8fb5-4b47-4a3d-aa59-9a1d4ea89a46_daily-value-check-did-the-system.md`
- `core/BUILD/results/SPEC_f57b8fb5-4b47-4a3d-aa59-9a1d4ea89a46_daily-value-check-did-the-system.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `PYTHONPATH=SERVICES/sunheart-brain python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_daily_value_check.py'` (4 OK)
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_tgbot_correction_wiring.py'` (6 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/daily_value_check.py SERVICES/sunheart-brain/curator/test_daily_value_check.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`
- `bash -n core/BUILD/activate/SPEC_f57b8fb5-4b47-4a3d-aa59-9a1d4ea89a46_daily-value-check-did-the-system.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/f57-registry.json`
- `systemd-analyze verify core/BUILD/cron/fpai-daily-value-check.service core/BUILD/cron/fpai-daily-value-check.timer` exited 0; sandbox emitted unrelated host/system-bus warnings.
- `git diff --check`

## Risks

- Live Telegram send, live timer install, and live `brain_index.corrections` write were not run in this sandbox.
- The one-line reply is consumed by the daily check only when an awaiting state exists; a normal message sent after the prompt will be treated as the feedback answer.
- The schema adds nullable `corrections.source`; existing correction rows remain valid with null source.

## Rollback

- Runtime pause: `touch /opt/fpai-build/.daily_value_check_disabled`.
- Full rollback: revert the listed files. If activated, also disable/remove `fpai-daily-value-check.timer` and `.service`, then run `systemctl daemon-reload`.

## Intent

Intent solved: James gets one low-friction daily value check and the reply becomes structured correction memory.

Downstream intent unlocked: the learning flywheel can inspect real daily usefulness feedback instead of relying only on incidental corrections.

Next unlocked move: after merge/activation on server 162, confirm the 20:00 Athens prompt sends once, the next one-line reply writes a `brain_index.corrections` row with `source='daily_value_check'`, and the state file moves from `awaiting_reply` to `captured`.
