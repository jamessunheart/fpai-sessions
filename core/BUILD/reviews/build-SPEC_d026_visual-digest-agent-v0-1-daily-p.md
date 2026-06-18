# AI Review — build/SPEC_d026_visual-digest-agent-v0-1-daily-p

**Verdict:** APPROVE · **Risk:** low

**Summary:** Read-mostly visual digest tool, in-scope with kill switch and no auto-install of the prod hook; minor cosmetic issues only.

## Findings
- No secrets hardcoded — Telegram token/chat_id sourced only from env or the existing curator module; brain_index read is a parameterized read-only SELECT with connect_timeout.
- Writes are confined to /opt/fpai-build/visuals/ and an ops_ledger append, matching the spec constraint; no main-branch, treasury, or identity/memory writes.
- systemd drop-in (core/BUILD/cron/...conf) targets the production fpai-morning-digest service but is an explicit review-only artifact and is NOT installed by this build — nothing fires automatically on merge.
- Kill switch VISUAL_DIGEST_DISABLE=1 present and tested; renderer-absent path exits 0 without writing a false artifact row.
- Minor (non-blocking): CLI --no-send substitutes a lambda returning True, so output reports sent=true and still appends a visual_digest ledger row despite no real send — cosmetic, could mislead the ledger.
- Minor: chromium invoked with --no-sandbox on self-generated local HTML; acceptable for trusted input but worth noting.
- Branch correctly based on feat/headless-build, registered in REGISTRY.json with status done (Ember-only merged), tests mock the renderer/sender so CI needs no Chromium.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
