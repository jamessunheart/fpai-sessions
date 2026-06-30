# SPEC_d133_d133-public-learning-interface-o Result

Status: done in working tree / awaiting independent AI review + merge.

Branch: `build/SPEC_d133_d133-public-learning-interface-o`

Note: the session contract requested a `codex/<slug>` branch, but this sandbox could not create `codex/d133-public-learning-interface` because the shared `.git` refs directory is read-only. The generated build branch is based on `feat/headless-build`.

## Summary

- Extended the isolated public `@sunheartai_bot` path behind `PUBLIC_CHAT_LIVE=0` default-off live gate.
- Added explicit first-contact consent before any public conversation text is stored.
- Stored consented conversation rows with `tier='PUBLIC'`, `source='public_chat'`, and consent metadata.
- Added probe-session-style engagement rows keyed as `public_chat:<chat_id>` so VPI/d132-style engagement metrics can consume public-chat activity.
- Routed generated public replies through `tools/privacy/public_context_pack.py` and a reusable `tools/privacy/canary_probe.py` validation helper before send/log.
- Fail closed to the public denial text if the public context pack or generated reply trips the canary gate.
- Updated the brain-index schema mirror and public bot systemd artifact.

## Tests

- `python3 -B -m unittest tools.public_bot.test_bot tools.privacy.test_public_context_pack tools.privacy.test_canary_probe SERVICES.sunheart-brain.curator.test_bot_mode_gate`
- `python3 -B -m tools.privacy.canary_probe`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/public_bot/bot.py tools/public_bot/test_bot.py tools/privacy/canary_probe.py tools/privacy/test_canary_probe.py tools/privacy/public_context_pack.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d133-registry.json`
- `systemd-analyze verify core/BUILD/cron/fpai-public-bot.service`
- `git diff --check`

## Independent Review

Attempted local `claude -p` independent review over the d133 diff. It returned `API Error: Unable to connect to API (ConnectionRefused)`, so independent AI review remains a pre-merge gate.

## Risks

- No live Telegram polling/send, live credential read, live `brain_index` write, deploy, push, merge, outreach, or money movement was performed.
- The generated spec references `core/BUILD/specs/SPEC_d133_public-learning-interface.md`, but that full spec file was not present in this checkout. This build used the generated d133 spec at `core/BUILD/specs/SPEC_d133_d133-public-learning-interface-o.md`.
- Live enablement still requires James/Ember to set `PUBLIC_CHAT_LIVE=1` after review and confirm the first public-chat consent/capture proof.

## Rollback

Revert the listed files. Runtime mitigation without reverting is to leave `PUBLIC_CHAT_LIVE` unset or `0`, or set `PUBLIC_BOT_DISABLE=1`. If the systemd service is later started, stop it with `systemctl disable --now fpai-public-bot.service`.

## Intent solved

The public bot can become the stranger-safe destination for outreach without exposing private/internal memory and without storing public conversation text before explicit consent.

## Downstream intent unlocked

Public-chat engagement and consented conversation rows can feed VPI, outcome learning, and Academy distillation after James-gated live activation.
