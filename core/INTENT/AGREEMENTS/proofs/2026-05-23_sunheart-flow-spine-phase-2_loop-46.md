---
loop: 46
slug: sunheart-flow-spine-phase-2
title: Sunheart Flow Spine · Phase 2 wire LIVE · TG voice → Linear CAPTURED
date: 2026-05-23
shipped_by: Ember (substrate-side · per Trust-tier 6 + "execute reversible without asking" policy)
---

# Proof · Loop 46 · Sunheart Flow Spine Phase 2 LIVE

## What shipped

The river is wired. Voice memos sent to `@sunheartbrain_bot` now auto-create Linear issues in CAPTURED with priority-current labels.

## End-to-end path

1. James sends voice memo to `@sunheartbrain_bot` (Telegram)
2. `sh-brain-tgbot.service` (162.0.208.88 · long-poller) receives update
3. Existing `_transcribe_voice()` calls OpenAI Whisper · returns text
4. NEW · `_linear_capture(transcript)` fires:
   - Detects voice-prefix (`rapid:` / `active:` / `slow:` / `dormant:`) → assigns priority current label (default `⚡ Rapid Current`)
   - Strips prefix from title body
   - POSTs to Linear GraphQL `issueCreate` mutation with team FUL · state CAPTURED · label
5. Returns issue URL · sends TG message: "🌊 Captured in the river · FUL-N · ⚡ Rapid Current"
6. Existing voice-out + brain-search + LLM-answer pipeline continues unaffected (capture is additive · not replacement)

## Files touched

| File | Change | Lines |
|---|---|---|
| `SERVICES/sunheart-brain/curator/tgbot.py` (local + server `/opt/sh-brain-src/curator/tgbot.py`) | Added Linear helpers (`_linear_token`, `_linear_label_lookup`, `_linear_capture`) + integration hook inside voice block | +137 |
| `/root/.config/fpai/linear/api.token` (server) | NEW · mode 600 · holds personal API key | 48 bytes |
| `/root/.config/fpai/linear/` (server) | NEW · mode 700 | dir |

## Defaults baked in (overridable via env)

```python
LINEAR_API_TOKEN_PATH=~/.config/fpai/linear/api.token
LINEAR_TEAM_ID=44963b86-9bc7-4cc1-8440-d094711408f8       # Full Potential AI · FUL
LINEAR_CAPTURED_STATE_ID=18529b8e-7c40-4e6d-9e36-d7e5082acfe1
```

## Voice-prefix detection

| Prefix | Label assigned |
|---|---|
| `rapid:` / `urgent:` | ⚡ Rapid Current (default) |
| `active:` / `flow:` | 🌀 Active Flow |
| `slow:` / `later:` | 🍃 Slow River |
| `dormant:` / `park:` / `someday:` | 💤 Dormant Pool |
| (no prefix) | ⚡ Rapid Current |

## Verification

- ✅ `tgbot.py` syntax-check PASS on both local + server
- ✅ Service `sh-brain-tgbot.service` restarted clean · `is-active = active`
- ✅ Boot logs show `curator.tgbot sh-brain-tgbot starting; polling messages + callback_query` · no import errors
- ✅ Linear function present on server (grep confirms `_linear_capture` at line 3540 + `Sunheart Flow Spine Phase 2` markers)
- ✅ Linear token deployed to server at correct path + mode 600
- ⏳ End-to-end voice-memo proof: pending James sending one voice memo to @sunheartbrain_bot to see the 🌊 captured reply with FUL-N URL

## Reversibility

HIGH. Rollback path: `cp /opt/sh-brain-src/curator/tgbot.py.bak-phase2-20260524-002357 /opt/sh-brain-src/curator/tgbot.py && systemctl restart sh-brain-tgbot.service`. Backup file is on the server.

## Failure modes (handled)

- **Linear API down** → `_linear_capture` returns None silently · existing voice-out + brain-search continues · TG ack ("🎙️ Heard:") still sent. No user-facing failure.
- **Token missing/wrong** → logged warning · returns None · same fallback.
- **Label cache empty** → issue still created without label (labelIds omitted from mutation if no match).
- **Network timeout** → 15s timeout · returns None · same fallback.

## Out of scope (deferred to next Phases)

- Phase 3 · AI Router auto-distillation (CAPTURED → DISTILLED with priority assignment by orchestrator)
- Phase 4 · Dashboard view of state counts + flow health %
- Phase 5 · HUMAN ASSIST routing to villagers via TG
- Phase 6 · BRICKCHAIN extraction from ARCHIVE/BRICK
- WhatsApp input gateway (Phase 2 is TG-only · simplest first per "one flow")
- Text-message capture via TG (only voice triggers Linear · text continues into brain-search pipeline as before)

## Composition

- `[[project-sunheart-flow-spine]]` — spec source · updated to mark Phase 2 LIVE
- `[[reference-linear-workspace]]` — canonical IDs used in deployment
- `[[feedback-no-outsourcing-to-james-what-substrate-can-do]]` — James-tap not required for this work-order's execution
- `[[feedback-just-execute-reversible]]` — policy ratified · executed without further Y/N

## Time

- Spec → ship: ~45 minutes substrate-side
- James input required: 0 (all reversible · Trust-tier 6 authorized)

## Next

The river awaits its first real drop. Send one voice memo to @sunheartbrain_bot · watch FUL-7 appear at https://linear.app/full-potential-ai/team/FUL/all
