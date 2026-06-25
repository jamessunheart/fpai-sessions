# SPEC_d079_whatsapp-channel-adapter-hermes Result

Status: done in working tree / independently reviewed / commit blocked by read-only shared Git metadata

## Files Changed

- `tools/hermes/whatsapp_adapter.py`
- `tools/hermes/wa_sender.py`
- `tools/hermes/contact_loader.py`
- `tools/hermes/test_wa_adapter.py`
- `tools/hermes/test_wa_sender.py`
- `tools/hermes/test_contact_loader.py`
- `core/STATE/CONTACT_POOL.md`
- `migrations/add_contact_pool_table.sql`
- `core/BUILD/specs/SPEC_d079_whatsapp-channel-adapter-hermes.md`
- `core/BUILD/results/SPEC_d079_whatsapp-channel-adapter-hermes.result.md`
- `core/BUILD/REGISTRY.json`

## Summary

Added a repo-side WhatsApp Hermes adapter for Meta WhatsApp Cloud API. The sender
supports session replies, pre-approved template messages, and `wa.me` onboarding
links. Outbound sends are dry-run/receive-only unless `WHATSAPP_LIVE=1` and
`DRY_RUN=0`; template sends also enforce a local 10/hour unverified-business
rate limit with an owner-only, timestamp-only ledger.

The webhook adapter verifies Meta `X-Hub-Signature-256`, parses inbound message
text/media/sender ids, exposes an optional FastAPI receiver at
`/webhooks/whatsapp`, creates or updates private `brain_index.contact_pool`
entries, seeds `brain_index.probe_pool`, records an engaged probe session, and
replies through the guarded WhatsApp sender.

The contact loader reads `name,channel,contact,notes` CSV rows or manual dicts
into `contact_pool`-shaped records. `core/STATE/CONTACT_POOL.md` documents the
private contact protocol, status flow, env vars, template, and privacy rules.
The SQL migration adds `brain_index.contact_pool` and extends `probe_pool` to
allow `platform='whatsapp'`.

## Tests

- `python3 -B -m unittest tools.hermes.test_email_adapter tools.hermes.test_reply_parser tools.hermes.test_wa_adapter tools.hermes.test_wa_sender tools.hermes.test_contact_loader tools.probe.test_probe` (42 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/hermes/whatsapp_adapter.py tools/hermes/wa_sender.py tools/hermes/contact_loader.py tools/hermes/test_wa_adapter.py tools/hermes/test_wa_sender.py tools/hermes/test_contact_loader.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d079-registry.json`
- `git diff --check`

## Review

Independent AI review completed. Initial review found blocker issues in
caller-dependent template rate limiting and undocumented `WA_APP_SECRET`. Follow-up
review found and verified fixes for private rate-ledger handling: no phone numbers
or template names are written, custom shared parent directories fail closed
without chmod, and injected-history rate-limited calls avoid filesystem mutation.
Final re-review reported no blocker findings.

## Commit Status

Blocked in this sandbox. `git add ...` failed because Git could not create
`/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d079_whatsapp-channel-adapter-hermes/index.lock`:
read-only file system. Current changes remain in the working tree on
`build/SPEC_d079_whatsapp-channel-adapter-hermes`, which descends from
`feat/headless-build`.

## Risks

The live database migration was not applied in this sandbox, and the optional
FastAPI receiver was not mounted into a live service. Real Meta sends require
James/Ember to provide `WA_PHONE_NUMBER_ID`, `WA_ACCESS_TOKEN`,
`WA_VERIFY_TOKEN`, `WA_APP_SECRET`, and explicitly set `WHATSAPP_LIVE=1`.
No live WhatsApp API calls, outreach sends, secrets, deploys, pushes, or merges
were performed.

## Rollback

Remove the new WhatsApp adapter/sender/contact-loader/test files, remove
`core/STATE/CONTACT_POOL.md`, remove `migrations/add_contact_pool_table.sql`,
remove this result artifact, and remove the d079 registry row. If the SQL
migration is later applied live, disable the mounted webhook and unset
`WHATSAPP_LIVE` before dropping `brain_index.contact_pool` or reverting the
`probe_pool` platform check.

## Intent

Intent solved: WhatsApp now has a guarded repo-side outreach and receive channel
path that can feed private contacts into the probe flow without changing the
existing Hermes gateway interface.

Downstream intent unlocked: Ember can apply the migration and mount the webhook
on a live host for receive-only proof, then James can explicitly bless a tiny
`WHATSAPP_LIVE=1` template batch after Meta template approval.
