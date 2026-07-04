# SPEC_d182_spec-d182-live-service-deploys-n Result

- Status: done in working tree / awaiting review + merge + guarded live activation proof
- Branch: `build/SPEC_d182_spec-d182-live-service-deploys-n`
- Cost: $0 marginal, repo-local tests only

## Summary

Added a mandatory guarded activation path for live-service deploys. `server_build_loop.sh` now runs activation scripts through `tools/build_loop/live_service_guard.py` instead of direct `bash`. The guard maps changed build targets to live services, snapshots known live files, runs the activation, smoke-tests the running service, restores the snapshot on failure, sends James one line (`dNNN deploy failed smoke-test, auto-reverted: <reason>`), and makes the build loop reset the accepted repo merge to `PRE_SHA` so failed live deploys are not treated as accepted.

For the bot incident class, the smoke verifies `sh-brain-tgbot.service` is active, fresh logs have no import/path errors, voice STT is importable, and the actual bot reply synthesis path does not label the response as `llama-fallback`.

Fixed the d177 regressions in the repo mirror:

- `claude -p` subprocesses now drop `ANTHROPIC_API_KEY` while preserving OAuth/subscription env.
- Voice STT readiness accepts the existing OpenAI Whisper fallback when `faster_whisper` is absent.
- `tgbot.py` helper loaders resolve through `FPAI_REPO_ROOT` or `/opt/fpai-build/FPAI_Cockpit`, not `/tools/...` from the live `/opt/sh-brain-src` path.
- The model-fallback alert path is covered so `telegram.send()` receives `chat_id` as a keyword.

Added `core/BUILD/activate/SPEC_d182_spec-d182-live-service-deploys-n.sh` to install the reviewed bot files after merge; the new guard owns backup/smoke/rollback around that activation.

## Tests

- `python3 -B -m unittest tools.build_loop.test_live_service_guard tools.build_loop.test_live_deploy_guard_contract tools.build_loop.test_liveness_probe tools.build_loop.test_auto_merge_governance`
- `python3 -B -m unittest SERVICES.sunheart-brain.curator.test_llm SERVICES.sunheart-brain.curator.test_voice_pipeline SERVICES.sunheart-brain.curator.test_tgbot_act_bridge SERVICES.sunheart-brain.curator.test_tgbot_model_health`
- `python3 -B -m unittest tools.build_loop.test_live_service_guard tools.build_loop.test_live_deploy_guard_contract tools.build_loop.test_liveness_probe tools.build_loop.test_auto_merge_governance tools.build_loop.test_revision_agent tools.build_loop.test_build_orphan_reaper`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/live_service_guard.py tools/build_loop/test_live_service_guard.py tools/build_loop/test_live_deploy_guard_contract.py SERVICES/sunheart-brain/curator/llm.py SERVICES/sunheart-brain/curator/test_llm.py SERVICES/sunheart-brain/curator/voice_pipeline.py SERVICES/sunheart-brain/curator/test_voice_pipeline.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_tgbot_act_bridge.py SERVICES/sunheart-brain/curator/test_tgbot_model_health.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d182-registry.json`
- `bash -n tools/build_loop/server_build_loop.sh core/BUILD/activate/SPEC_d182_spec-d182-live-service-deploys-n.sh`
- `git diff --check`

## Proof

Unit proof covers a deliberately failed bot smoke: the guard detects inactive `sh-brain-tgbot.service`, restores the backed-up live `tgbot.py`, and sends exactly one alert containing `d182 deploy failed smoke-test, auto-reverted: sh-brain-tgbot.service is not active`.

Static proof covers the server loop contract: activation scripts call `live_service_guard.py`, failed post-deploy smoke resets the repo to `PRE_SHA`, and the build is held as `changes`.

## Risks

No live Telegram message, real `systemctl`, real `journalctl`, or live `/opt/sh-brain-src` mutation was run in this sandbox. The full Done proof still requires server 162 to run the guarded d182 activation and observe either a good smoke pass or an intentional test-service smoke failure/revert.

The initial live-service map is intentionally conservative: it covers the known bot/intake/guide/site paths and generic `systemctl` activation parsing. Additional services should be added to `TARGETS` as they get activation scripts.

## Rollback

Revert this branch. If d182 activation has already run live, the guard writes timestamped backups under `/opt/fpai-build/deploy-backups/<spec>-<stamp>/`; restore the relevant manifest files and restart `sh-brain-tgbot.service`.

## Intent

- Intent solved: live-service activation cannot be accepted solely because review passed; it now requires a running-service smoke test with rollback.
- Downstream intent unlocked: autonomous live deploys can resume with a mandatory post-deploy guardrail instead of relying on diff review as a proxy for live behavior.
- Next move: after merge on server 162, run the guarded activation and then deliberately break a test service or canary target to prove smoke failure auto-reverts with the one-line James alert.
