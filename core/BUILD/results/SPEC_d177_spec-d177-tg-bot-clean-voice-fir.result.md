# SPEC d177 — TG bot clean, voice-first, self-aware, able to ACT

Status: done in repo mirror / awaiting review, merge, activation, and live Telegram proof.

## Files Changed

- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/test_tgbot_act_bridge.py`
- `deploy-tools/kai-bridge.py`
- `deploy-tools/triad-bridge.py`
- `core/BUILD/activate/SPEC_d177_spec-d177-tg-bot-clean-voice-fir.sh`
- `core/BUILD/results/SPEC_d177_tg_push_inventory.md`
- `core/BUILD/specs/SPEC_d177_spec-d177-tg-bot-clean-voice-fir.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

- Added an honest TG bot self-model in the private chat system prompt and a `/whatcanyoudo` command.
- Added deterministic owner-intent classification for question, build request, decision, journal, and ordinary chat.
- Added an ACT bridge that writes owner build/change requests into `brain_index.decisions` as `status='answered'`, `needs_build=true`, `spec_written=false`, with collision-safe `dNNN` ids and an ETA confirmation.
- Added captured non-build rows for decision/journal intents, so the bot does not pretend to execute reserved actions.
- Kept the voice-first path: voice note downloads, transcribes, shows the transcript, captures to Linear, then routes the transcript before normal RAG chat.
- Made CORA Kai/Triad intermediate Telegram pings opt-in via `CORA_BRIDGE_TELEGRAM_ALERTS=1`; lead alerts remain unchanged.
- Added a pusher inventory and activation script. Activation installs the reviewed TG bot, installs quieted CORA bridge copies if live paths exist, restarts `sh-brain-tgbot.service`, and disables `zv-morning-digest.timer` if present.

## Tests

- `python3 -B -m unittest SERVICES.sunheart-brain.curator.test_tgbot_act_bridge SERVICES.sunheart-brain.curator.test_tgbot_constitution SERVICES.sunheart-brain.curator.test_voice_pipeline SERVICES.sunheart-brain.curator.test_tgbot_model_health` — 13 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_tgbot_act_bridge.py deploy-tools/kai-bridge.py deploy-tools/triad-bridge.py`
- `bash -n core/BUILD/activate/SPEC_d177_spec-d177-tg-bot-clean-voice-fir.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d177-registry-building.json`
- `git diff --check`

## Proof

- Unit proof confirms `build/fix/change` requests become buildable payloads matching the pending-build predicate.
- Unit proof confirms “what built overnight?” stays a question, not a queued build.
- Unit proof confirms `/whatcanyoudo` names both capabilities and hard limits.
- Static proof confirms changed Python and activation shell parse cleanly.

## Live Proof Still Needed

This sandbox did not send live Telegram messages, mutate live `brain_index`, disable live timers, or restart live services.

After merge/activation on server 162:

1. Send voice memo: “build a tiny proof that the bot can queue voice requests”.
2. Confirm transcript appears, Linear capture is attempted, a `dNNN` row is inserted with `status='answered'`, `needs_build=true`, `spec_written=false`, and the bot replies with the id + ETA.
3. Run `/whatcanyoudo` and confirm the honest can/cannot list.
4. Confirm `zv-morning-digest.timer` is disabled or rerouted.
5. Confirm `fpai-morning-digest.timer`, lead alerts, build alerts, spend alerts, and d174 model-degrade alerts still fire.

## Risks

- Intent classification is regex-first and conservative, not LLM-classified. Imperative words such as `run`, `deploy`, `restart`, `ssh`, `git`, and `merge` intentionally queue for the builder instead of executing.
- Live `brain_index.decisions` schema is assumed to support the columns already used by build-loop rows: `id`, `question`, `answer`, `status`, `needs_build`, `spec_written`, `build_spec`, `proof_expected`, `liveness`, `build_status`, `created_at`.
- The activation script disables only `zv-morning-digest.timer`; older pulse/stream/Adam scripts still require live loaded-unit/cron review before disabling.

## Rollback

- Revert this branch.
- If activated, restore files from `/opt/sh-brain-src/.d177-backup-*`, then `systemctl restart sh-brain-tgbot.service`.
- Re-enable ZV digest only if it has an approved channel: `systemctl enable --now zv-morning-digest.timer`.
- To re-enable CORA bridge pings without code rollback, set `CORA_BRIDGE_TELEGRAM_ALERTS=1` in the relevant live bridge environment.

## Intent Solved

James can send a voice/text build/change/decision signal to the TG bot and get an honest routed result instead of a chat-only answer or an over-claimed direct action.

## Downstream Intent Unlocked

Telegram becomes a same-brain upstream capture surface for the autonomous build loop: voice memo -> transcript -> `dNNN` queue row -> builder loop pickup -> proof.
