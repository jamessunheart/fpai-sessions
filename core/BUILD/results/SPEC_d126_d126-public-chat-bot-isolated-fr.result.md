# SPEC d126 Result — Public Chat Bot

Status: done in working tree / awaiting merge review

## Files changed

- `tools/public_bot/__init__.py`
- `tools/public_bot/bot.py`
- `tools/public_bot/test_bot.py`
- `SERVICES/sunheart-brain/index/schema.sql`
- `core/BUILD/cron/fpai-public-bot.service`
- `core/BUILD/activate/SPEC_d126_d126-public-chat-bot-isolated-fr.sh`
- `core/BUILD/specs/SPEC_d126_d126-public-chat-bot-isolated-fr.md`
- `core/BUILD/results/SPEC_d126_d126-public-chat-bot-isolated-fr.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added an isolated public Telegram long-poller for `@sunheartai_bot`. It loads the public token from `PUBLIC_TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_TOKEN`, `BOT_TOKEN`, or `~/.config/fpai/tg_sunheartai/creds.cache`, greets new chats with `core/STATE/OUTREACH_VOICE.md`, replies through `claude -p` with only the Sunheart outreach persona as the system prompt, caps outbound replies to 220 whitespace tokens, and refuses private/internal probes.

The bot logs only to the new `brain_index.public_conversations` table and has a source-level regression test proving it does not import curator modules or query private brain tables. `PUBLIC_BOT_DISABLE=1` stops all sends. Rate limiting is file-backed per chat/global, reusing the existing probe governor constants without calling its private DB-read path.

The reviewed systemd artifact is `fpai-public-bot.service`. The activation script installs the unit but does not start it unless `PUBLIC_BOT_ACTIVATE=1`, preserving the spec's "James flips it live" next move.

## Tests

- `python3 -B -m unittest tools.public_bot.test_bot` (8 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/public_bot/bot.py tools/public_bot/test_bot.py`
- `bash -n core/BUILD/activate/SPEC_d126_d126-public-chat-bot-isolated-fr.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks

Live Telegram polling/sending, live `claude -p`, and live Postgres writes were not exercised in this sandbox. The live proof still needs James/Ember to set the public bot token/env, start with `PUBLIC_BOT_ACTIVATE=1`, send a harmless test DM to `@sunheartai_bot`, and verify the reply plus the `brain_index.public_conversations` row. The token cap uses whitespace-token bounding, not a model tokenizer.

## Rollback

Set `PUBLIC_BOT_DISABLE=1` for immediate no-send behavior. If activated, run `systemctl disable --now fpai-public-bot.service`, remove `/etc/systemd/system/fpai-public-bot.service`, and `systemctl daemon-reload`. To remove stored public chat logs, drop `brain_index.public_conversations`.

## Intent solved

Real people now have a repo-reviewed public chat entrypoint that is separate from the private Sunheart Brain bot.

## Downstream intent unlocked

James can explicitly flip the isolated public bot live, then discovery/probe flows can route first conversations to `@sunheartai_bot` without exposing private memory.
