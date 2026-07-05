# SPEC_d191_spec-d191-ingest-the-doctrine-bo Result

build_kind=activated

## Summary

Added repo-doctrine ingestion so the six governing doctrine files in `core/STATE` become embedded `brain_index.note_chunks` rows tagged `doctrine`: `CORE_DOCTRINE.md`, `ALLOCATION_INTELLIGENCE.md`, `CONSTITUTION.md`, `STEWARDSHIP_CONSTITUTION.md`, `AI_PRINCIPLES.md`, and `FOUNDATION.md`. The ingest helper prefixes each file with source path, repo commit, file-updated timestamp, and a freshness rule before sending it through the existing local embedding endpoint.

Extended the brain-index ingest endpoint to accept `repo-doctrine/...` source paths while preserving existing `memory-git/...` behavior. Doctrine rows use `source='repo-doctrine'`, public sensitivity, local embeddings, and rollback-friendly `source_path` values.

Injected bounded `CORE_DOCTRINE.md` boot-spine context into the Telegram bot system prompt before HOT_STATE, with `SH_CORE_DOCTRINE_MAX_CHARS` and `SH_CORE_DOCTRINE_DISABLE` controls. Bot search hits now carry `source_path` and `updated_at` into synthesis, and doctrine/law/principle answers are instructed to name the doctrine file and updated date.

Added a d191 activation script and 30-minute systemd refresh timer. Activation installs the changed bot/index files, restarts `sh-brain-index.service` and `sh-brain-tgbot.service`, enables `fpai-doctrine-ingest.timer`, and runs one immediate doctrine ingest. The d182 live-service guard now backs up/smokes the brain-index service as well as the bot for this class of change.

## Files Changed

- `SERVICES/sunheart-brain/index/ingest_routes.py`
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `tools/doctrine/ingest.py`
- `tools/doctrine/test_ingest.py`
- `tools/build_loop/live_service_guard.py`
- `tools/build_loop/test_live_service_guard.py`
- `core/BUILD/cron/fpai-doctrine-ingest-run.sh`
- `core/BUILD/cron/fpai-doctrine-ingest.service`
- `core/BUILD/cron/fpai-doctrine-ingest.timer`
- `core/BUILD/activate/SPEC_d191_spec-d191-ingest-the-doctrine-bo.sh`
- `core/BUILD/specs/SPEC_d191_spec-d191-ingest-the-doctrine-bo.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d191_spec-d191-ingest-the-doctrine-bo.result.md`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.doctrine.test_ingest SERVICES.sunheart-brain.curator.test_build_context tools.build_loop.test_live_service_guard` — 29 OK
- `python3 -B -m unittest SERVICES.sunheart-brain.curator.test_tgbot_constitution SERVICES.sunheart-brain.curator.test_tgbot_model_health tools.build_loop.test_activation_policy tools.build_loop.test_activation_policy_contract` — 14 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/doctrine/ingest.py tools/doctrine/test_ingest.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/index/ingest_routes.py tools/build_loop/live_service_guard.py tools/build_loop/test_live_service_guard.py`
- `bash -n core/BUILD/cron/fpai-doctrine-ingest-run.sh core/BUILD/activate/SPEC_d191_spec-d191-ingest-the-doctrine-bo.sh`
- `python3 tools/doctrine/ingest.py --repo . --dry-run --json` — found all 6 `repo-doctrine/core/STATE/...` source paths
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d191_spec-d191-ingest-the-doctrine-bo --base-ref feat/headless-build --head-ref HEAD`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d191-registry.json`
- `git diff --check`

## Live Verification

Live DB/bot proof was not run in this sandbox. Post-merge activation on server 162 should run `core/BUILD/activate/SPEC_d191_spec-d191-ingest-the-doctrine-bo.sh` through the d182 guard, then confirm:

- `fpai-doctrine-ingest.service` writes rows where `source='repo-doctrine'`, `tags` contains `doctrine`, and `source_path` starts with `repo-doctrine/core/STATE/`.
- `brain_search` returns doctrine chunks for Allocator role, P21, 5 Allocation Laws, and Crystal queries.
- The Telegram bot answers those questions from the actual doctrine and names the file/date.
- The bot context contains the `CORE DOCTRINE BOOT SPINE` block.

## Risks

- Full semantic retrieval proof requires live server DB, local Ollama, ingest token, and bot service activation.
- If `/etc/sh-brain/curator.env` or `/etc/sh-brain/index.env` lacks an ingest token, the timer will fail loudly instead of silently pretending doctrine is fresh.
- The activation restarts `sh-brain-index.service` and `sh-brain-tgbot.service`; d182 guard handles rollback for the changed live files.

## Rollback

Revert this branch. If already activated, disable `fpai-doctrine-ingest.timer`, restore the previous live `build_context.py`, `tgbot.py`, and `ingest_routes.py` from the d182 guard backup, restart `sh-brain-index.service` and `sh-brain-tgbot.service`, and optionally delete doctrine rows with:

```sql
DELETE FROM brain_index.note_chunks WHERE source_path LIKE 'repo-doctrine/%';
```

## Intent Solved

The governing doctrine is no longer terminal-only context. It has a repo-to-embedding path, freshness metadata, scheduled refresh, and top-of-context boot-spine injection for the owner bot.

## Downstream Intent Unlocked

James can ask the Telegram brain about the Allocator role, P21, the 5 Allocation Laws, and the Crystal and get answers grounded in the actual doctrine instead of partial HOT_STATE/chat memory.
