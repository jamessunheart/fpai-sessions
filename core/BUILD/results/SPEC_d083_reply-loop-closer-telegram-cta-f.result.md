# SPEC_d083_reply-loop-closer-telegram-cta-f Result

- Status: done in working tree / awaiting merge review
- Branch: `build/SPEC_d083_reply-loop-closer-telegram-cta-f`
- Files changed:
  - `tools/probe/followup.py`
  - `tools/probe/inbound_webhook.py`
  - `tools/probe/test_followup.py`
  - `tools/probe/test_inbound.py`
  - `core/BUILD/server209/email_to_brain.py`
  - `core/BUILD/cron/fpai-probe-followup.service`
  - `core/BUILD/cron/fpai-probe-followup.timer`
  - `core/BUILD/cron/fpai-probe-inbound.service`
  - `SERVICES/sunheart-brain/nginx/brain.sunheart.com.conf`
  - `tools/probe/schema.sql`
  - `core/BUILD/specs/SPEC_d083_reply-loop-closer-telegram-cta-f.md`
  - `core/BUILD/REGISTRY.json`
  - `docs/codex/HANDOFF.md`

## Summary

Added the d083 reply-loop closer without activating any live infra.

Part 1 adds `tools/probe/followup.py`, which finds email-backed `probe_sessions` with no engagement after 3 days, skips sessions already marked `tg_cta_sent`, sends the exact Telegram CTA follow-up through the existing Brevo live/dry-run gates, claims live sends before Brevo to avoid duplicate overlapping sends, releases the claim on failed sends so transient failures can retry, and appends `tg_cta_sent` only after a successful Brevo send.

Part 2 adds `tools/probe/inbound_webhook.py`, a guarded FastAPI app for `POST /probe/inbound-reply`. It defaults disabled unless `PROBE_PIPE_ENABLED=1`, requires a matching `PROBE_PIPE_TOKEN`, matches replies by `message_id`/`in_reply_to` or sender email, inserts a pending row into `brain_index.probe_reply_queue`, marks `probe_sessions.engaged = true`, and stores the inbound body as the latest message. The server-209 pipe script is included as `core/BUILD/server209/email_to_brain.py` for later deployment to `/home/fpai/scripts/email_to_brain.py` after explicit James approval.

Systemd/nginx artifacts are repo-only: `fpai-probe-followup.service` + `.timer` for daily follow-ups, `fpai-probe-inbound.service` for the localhost `8771` app, and a TLS nginx proxy route at `https://brain.sunheart.com/probe/inbound-reply`.

## Tests

- `env -u OUTREACH_EMAIL_FROM python3 -B -m unittest tools.probe.test_followup tools.probe.test_inbound tools.probe.test_probe tools.hermes.test_email_adapter tools.hermes.test_reply_parser` — 36 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/probe/followup.py tools/probe/inbound_webhook.py tools/probe/test_followup.py tools/probe/test_inbound.py core/BUILD/server209/email_to_brain.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d083-registry.json`
- `git diff --check`
- Independent AI review: initial P2 findings fixed; final blocker-only re-review found no remaining P1/P2 blockers.

## Risks

- No live email was sent and no live timer/service was installed in this sandbox.
- The spec named both `8770` and `8771`; this branch implements the standalone app on localhost `8771` and a TLS nginx proxy at `https://brain.sunheart.com/probe/inbound-reply`. `PROBE_INBOUND_URL` can point elsewhere only with the same token guard.
- `PROBE_PIPE_ENABLED` must stay unset/false until server 209 pipe delivery is verified with a test email.
- `PROBE_PIPE_TOKEN` must be set on both server 209 and server 162 before enabling the pipe.
- The inbound webhook queues pending reply rows, but a consumer that composes/sends those replies should be verified or specified before assuming full auto-reply behavior.

## Rollback

- Disable follow-ups by not installing/removing `fpai-probe-followup.timer` or setting `PROBE_DISABLE=1` / `OUTREACH_EMAIL_DISABLE=1`.
- Disable inbound reply processing by leaving `PROBE_PIPE_ENABLED` unset or setting it to `0`.
- Full code rollback: revert the d083 files listed above and remove the d083 registry/result/handoff entries.

## Intent

- Intent solved: outreach replies can route away from James's inbox toward Telegram automation, with email replies captured by a guarded pipe path.
- Downstream intent unlocked: Ember can run a live disabled/dry-run proof on 162, then James can explicitly authorize the server-209 valias/script deployment and one test email before enabling `PROBE_PIPE_ENABLED=1`.
