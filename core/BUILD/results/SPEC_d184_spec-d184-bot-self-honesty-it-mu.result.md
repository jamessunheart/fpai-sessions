# SPEC d184 — Bot Self-Honesty Result

- Status: done in working tree / awaiting review + guarded activation
- Branch: `build/SPEC_d184_spec-d184-bot-self-honesty-it-mu`

## Files Changed

- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/systemd/sh-brain-tgbot.service`
- `SERVICES/sunheart-brain/curator/test_tgbot_model_health.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `core/BUILD/activate/SPEC_d184_spec-d184-bot-self-honesty-it-mu.sh`
- `core/BUILD/specs/SPEC_d184_spec-d184-bot-self-honesty-it-mu.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

The private TG bot now has a shared read-only self-check state used by reply footers, `/health`, and startup self-test. It reports:

- actual answer model label, including `⚠️ on fallback model` when Claude falls through to Ollama;
- HOT_STATE path, size, age, empty/stale state, and terse footer wording when live state is old;
- voice STT availability, accepting either `faster_whisper` or OpenAI Whisper fallback;
- queue-write reachability by checking `brain_index.decisions` existence and insert privilege without writing a row;
- recent import/degrade/error/fallback warnings from `journalctl` for `sh-brain-tgbot.service`.

Startup now runs a Claude ping, HOT_STATE read, STT dependency check, queue reachability check, and recent-log scan. If any check is degraded it sends one line to James/ops: `bot started degraded: <what>`.

The baked fragility fixes are permanent in repo/config:

- `llm._claude_cli_env()` already strips `ANTHROPIC_API_KEY` for Claude CLI subprocesses.
- `sh-brain-tgbot.service` now sets `CURATOR_LLM_PROVIDER=claude-cli`, blanks `ANTHROPIC_API_KEY`, and sets `SH_HOT_STATE_MAX_CHARS=3500`.
- d184 activation also patches `/etc/sh-brain/curator.env` to keep those defaults without relying on a drop-in.
- `build_context.py` defaults `SH_HOT_STATE_MAX_CHARS` to `3500` instead of `0`.
- voice STT readiness and transcription retain OpenAI Whisper fallback when `faster_whisper` is absent.

## Tests

- `python3 -B -m unittest SERVICES.sunheart-brain.curator.test_tgbot_model_health SERVICES.sunheart-brain.curator.test_voice_pipeline SERVICES.sunheart-brain.curator.test_build_context` (28 OK)
- `python3 -B -m unittest tools.build_loop.test_live_service_guard tools.build_loop.test_live_deploy_guard_contract tools.build_loop.test_liveness_probe tools.build_loop.test_auto_merge_governance` (17 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/llm.py SERVICES/sunheart-brain/curator/voice_pipeline.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_tgbot_model_health.py SERVICES/sunheart-brain/curator/test_build_context.py`
- `bash -n core/BUILD/activate/SPEC_d184_spec-d184-bot-self-honesty-it-mu.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d184-registry.json`
- `git diff --check`

## Proof

Unit proof covers fallback answer footer, startup degraded alert aggregation, `/health` full-state rendering, OpenAI Whisper fallback readiness, and HOT_STATE default bounding at about 3500 chars.

The d182 smoke/guard tests still pass in this branch, so the guarded live activation path remains intact.

## Risks

Live forced degradation was not run in this sandbox. The remaining Done proof requires guarded activation on server 162, then forcing Claude auth failure and confirming:

- the next substantive bot reply footer says `⚠️ on fallback model`;
- service restart sends one `bot started degraded: ...` alert;
- `/health` reports model/context/voice/queue/log truthfully;
- the service is green again after auth/config restoration.

Recent log warnings are read from `journalctl`; if systemd journal access is unavailable, the bot treats that signal as no warnings rather than failing replies.

## Rollback

Revert this branch. If activation already ran live, restore curator files from the d182 guard backup, restore the prior `sh-brain-tgbot.service`/`curator.env`, run `systemctl daemon-reload`, and restart `sh-brain-tgbot.service`.

## Intent

- Intent solved: the private TG bot tells James when its model, live state, voice intake, queue path, or imports/logs are degraded instead of silently answering from a broken state.
- Downstream intent unlocked: voice-memo-to-build, chat approvals, briefings, and alerts can proceed only after the bot self-check is green and visible.
- Next unlocked move: review/activate d184 through the d182 guarded live-service path, then perform the forced-degrade proof on server 162.
