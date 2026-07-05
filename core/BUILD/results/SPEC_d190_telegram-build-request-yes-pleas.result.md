# SPEC d190 — Telegram hands-free steering

Status: done in working tree / awaiting review + merge + activation.

## Files Changed

- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/test_tgbot_act_bridge.py`
- `core/BUILD/activate/SPEC_d190_telegram-build-request-yes-pleas.sh`
- `core/BUILD/specs/SPEC_d190_telegram-build-request-yes-pleas.md`
- `core/BUILD/results/SPEC_d190_telegram-build-request-yes-pleas.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

- Added a safe hands-free steering parser for owner Telegram messages before ordinary ACT-bridge classification.
- Natural text/voice phrases now route to existing safe command handlers:
  - "what's building right now" -> `/builds`
  - "show pending approvals" -> `/pending`
  - "what needs my decision" -> `/decisions`
  - "what can you do" -> `/whatcanyoudo`
  - "health check" -> `/health`
  - "voice on/off/status" -> `/voice ...`
- Dangerous/action phrases containing build, fix, deploy, restart, run, ssh, bash, git, merge, send, pay, buy, sell, or move-money language do not map to direct commands and continue through the queue/protection path.
- Added an activation script that installs only the reviewed `tgbot.py`, compiles it, reloads systemd, and restarts `sh-brain-tgbot.service`.

## Tests

- `python3 -B -m unittest SERVICES.sunheart-brain.curator.test_tgbot_act_bridge SERVICES.sunheart-brain.curator.test_tgbot_constitution SERVICES.sunheart-brain.curator.test_tgbot_model_health` — 17 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_tgbot_act_bridge.py`
- `bash -n core/BUILD/activate/SPEC_d190_telegram-build-request-yes-pleas.sh`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d190_telegram-build-request-yes-pleas --base-ref feat/headless-build --head-ref HEAD` — OK: activation script present
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d190-registry-done.json`
- `git diff --check`

## Proof

- Unit proof confirms spoken steering phrases map to the intended existing commands.
- Unit proof confirms dangerous action phrases return `None`, so they are not silently executed as commands.
- Message-handler proof confirms an owner text status phrase calls `/builds`, sends the command result, and does not call `_queue_owner_intent`.

## Live Proof Still Needed

This sandbox did not send live Telegram messages, mutate live `brain_index`, restart live services, push, merge, or deploy.

After merge/activation on server 162:

1. Send a voice memo: "what's building right now" and confirm the bot replies with the `/builds` snapshot and voice-out if enabled.
2. Send "show pending approvals" and confirm the existing `/pending` approval surface appears.
3. Send "build a hands-free steering proof" and confirm it still queues a `dNNN` builder row instead of acting directly.

## Risks

- Phrase matching is deterministic and conservative; unrecognized steering phrasing falls back to normal chat or queue classification.
- `/pending` can send button messages and return `None`; the steering adapter preserves that existing behavior.
- Activation restarts the Telegram bot service after merge, so live proof should be watched immediately.

## Rollback

- Revert this branch.
- If activated, restore `tgbot.py` from `/opt/sh-brain-src/.d190-backup-*` and run `systemctl restart sh-brain-tgbot.service`.

## Intent Solved

James can steer the build loop by voice/text with natural status and decision phrases instead of needing exact slash commands.

## Downstream Intent Unlocked

Telegram becomes a safer hands-free control surface: listen -> ask status/decision state -> queue next build -> receive proof, without granting the bot terminal/deploy/money powers.
