# SPEC d174 Result — TG Bot Loud Fallback + Context Quality

## Status
Done in repo mirror; live deploy/test is queued through activation script after merge.

## Files Changed
- `SERVICES/sunheart-brain/curator/llm.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/test_llm.py`
- `SERVICES/sunheart-brain/curator/test_tgbot_model_health.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `tools/build_loop/health_check.sh`
- `core/BUILD/activate/SPEC_d174_spec-d174-tg-bot-loud-model-fall.sh`
- `core/BUILD/specs/SPEC_d174_spec-d174-tg-bot-loud-model-fall.md`
- `core/BUILD/REGISTRY.json`

## Summary
Claude CLI fallback is no longer silent. `llm.py` now returns `fallback_from` and `fallback_reason` when `claude -p` falls through to Ollama, with the fallback model default aligned to `llama3.2:3b`. `tgbot.py` now:

- logs a warning for every fallback;
- sends the one-line ops Telegram alert: `⚠️ TG bot fell back to llama3.2:3b — claude -p: <reason>`;
- writes `/var/lib/sh-brain/model_health.json` counters for reply fallback and startup self-test failure;
- runs a startup `claude -p` self-test before polling messages and alerts immediately on failure;
- appends `Model: Sonnet` or `Model: llama-fallback` to each synthesized private reply;
- logs rough prompt-token estimates against `SH_TGBOT_PROMPT_TOKEN_LIMIT`.

Context caps were raised for Sonnet:

- RAG hits default `8 -> 10`;
- RAG hit chars remain/are explicit at `1200`;
- recent chat history is injected at `20` turns by default;
- HOT_STATE is full by default via `SH_HOT_STATE_MAX_CHARS=0` while other build-context caps remain bounded.

`tools/build_loop/health_check.sh` now surfaces the model-health counter and fails health when the bot is degraded.

## Unsolicited TG Push Inventory
Repo-visible push sources found:

- `fpai-morning-digest` plus drop-ins `SPEC_d026_fpai_morning_digest_visual_post.conf` and `SPEC_d033_fpai_morning_digest_backup_status.conf` — wanted daily digest lane; keep consolidated to one daily digest.
- `tools/build_loop/build_alerts.py` / build loop notifier — wanted event-triggered build START/REVIEW/MERGED/FAILED/VERIFIED alerts.
- `tools/probe/imap_poller.py`, `tools/ads/campaign_watch.py`, `tools/burn/reconcile.py` — wanted event alerts only for lead-in, campaign/billing threshold, provider-burn red paths.
- `fpai-awareness-reliability`, `fpai-failure-watchdog`, `fpai-security-sentinel`, `fpai-post-merge-reality` with `--send-alert` — wanted only for red-path failures.
- `SERVICES/sunheart-brain/curator/daily_value_check.py` — daily James prompt; interruption-worthy only if James still wants the explicit value check.
- `infra/launchagents/com.sunheart.pulse-daily.plist` and `infra/scripts/pulse_daily_prompt.sh` — daily pulse prompt; candidate to fold into the one daily digest/value check lane.
- `infra/launchagents/com.sunheart.narrator-pulse.plist`, `infra/scripts/meta_narrator_run.sh`, and `infra/scripts/stream_to_tg.sh` — older brain-to-TG/pulse streaming path; candidate to disable after live inventory confirms it is still loaded.
- `tools/beacon/seed_content_bank.py`, `tools/horizon/scanner.py`, `tools/forge/frontier_scan.py`, `tools/recursive_improver.py`, `tools/mirror/digest.sh`, backup helpers, and merge/process scripts — notifier-capable; should stay silent by default unless event severity earns interruption.

Consolidation rule implemented for this spec's new alert: model degrade is event-triggered only. No live timers/LaunchAgents were disabled in this sandbox because that would be a live operational change outside the writable repo and needs operator confirmation of what is actually loaded.

## Tests
- `python3 -B -m unittest SERVICES.sunheart-brain.curator.test_llm SERVICES.sunheart-brain.curator.test_tgbot_model_health SERVICES.sunheart-brain.curator.test_build_context` — 22 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/llm.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_llm.py SERVICES/sunheart-brain/curator/test_tgbot_model_health.py SERVICES/sunheart-brain/curator/test_build_context.py`
- `bash -n tools/build_loop/health_check.sh core/BUILD/activate/SPEC_d174_spec-d174-tg-bot-loud-model-fall.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d174-registry-building.json`
- `git diff --check`

## Live Proof Still Required
After merge on server 162:

1. Run activation script or let the build loop run it.
2. Confirm `systemctl status sh-brain-tgbot.service` is active.
3. Message the bot a current-state question and verify answer quality plus `Model: Sonnet`.
4. Temporarily break Claude CLI auth or set `CURATOR_CLAUDE_CLI_BIN` to a missing binary in a reversible service override, restart the bot, and confirm the startup alert fires.
5. Restore auth/override and confirm `/var/lib/sh-brain/model_health.json` shows counters and `tools/build_loop/health_check.sh` surfaces them.

## Risks
- The live `/opt/sh-brain-src` tree was readable but not writable from this sandbox, so deployment is via activation script.
- Visible `Model: ...` footers make the bot truthful but add one line to otherwise terse replies.
- HOT_STATE full context increases prompt size; rough token estimates are logged, but the live model-limit proof requires a real server message.

## Rollback
- Revert this branch.
- Runtime rollback after activation: restore `tgbot.py`, `llm.py`, and `build_context.py` from `/opt/sh-brain-src/.d174-backup-*`, then `systemctl restart sh-brain-tgbot.service`.

## Intent Solved
TG bot model degradation is loud, counted, and visible per reply instead of silently becoming a weak local model.

## Downstream Intent Unlocked
James can trust Telegram as a same-brain interface again because model auth failure becomes an interrupting ops signal rather than hidden answer-quality drift.
