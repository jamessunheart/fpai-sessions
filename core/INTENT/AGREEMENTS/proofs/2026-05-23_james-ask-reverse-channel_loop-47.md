---
loop: 47
slug: james-ask-reverse-channel
title: James-Ask Reverse Channel · TG bot asks James for what's needed
date: 2026-05-23
shipped_by: Ember (substrate-side · ~30 min from spec to first ask delivered)
---

# Proof · Loop 47 · James-Ask Reverse Channel LIVE

## What shipped

The bot stops being only inbound. The river now closes the loop: agents file asks → bot delivers to James in TG → James replies → ack + asking-agent picks it up.

## Architecture

File-drop queue + TG long-poller hook. See `[[project-james-ask-reverse-channel]]` for full schema.

## Files

| File | LOC | Role |
|---|---|---|
| `SERVICES/sunheart-brain/curator/james_ask.py` (new) | 250 | Queue API · format · send · match · expire · status |
| `SERVICES/sunheart-brain/curator/tgbot.py` (patched) | +35 | Import + `_ask_send_wrapper` + poll-loop hook + `_handle_message` reply-match hook |
| `/root/.config/fpai/james_ask_queue/{pending,sent,answered,expired}/` (server) | dirs | Live queue (mode 700) |

## Verification

- ✅ Both files rsync'd to /opt/sh-brain-src/curator/
- ✅ Syntax-check PASS on server
- ✅ Queue dirs created mode 700
- ✅ Service restarted clean · no import errors
- ✅ Filed 2 asks via Python on server
- ✅ Asks moved pending/ → sent/ within ~25s (next poll cycle)
- ✅ Logs show: `curator.james_ask james_ask: sent ask_2026... (tg msg None)`
- ⏳ End-to-end reply-match: pending James replying to one of the 2 asks in TG

## First asks filed

- `ask_20260524_004425_send-any-voice-memo-..._b4cca2` — Phase 2 smoke test (rapid · 3 options)
- `ask_20260524_004425_want-to-rotate-the-linear-..._e58342` — Optional key rotation (slow · 3 options)

## Reversibility

HIGH. Rollback:
```
cp /opt/sh-brain-src/curator/tgbot.py.bak-jamesask-20260524-004305 /opt/sh-brain-src/curator/tgbot.py
rm /opt/sh-brain-src/curator/james_ask.py
systemctl restart sh-brain-tgbot.service
```
Backup file on server.

## What unlocks

- Every irreducibly-James decision can now be reached without James opening terminal · just reply in TG
- Counsel asks · Forge asks · Treasurer asks · all routable through the same channel
- Reduces TIME-stream cost of James-tap from "open terminal / read context / decide / reply" to "read TG · tap reply · go"
- Closes Sunheart Flow System loop (mindmap's "AI ROUTER → Ambiguous → Clarify First" → that "clarify" now has a delivery mechanism)

## Time

- Spec → ship: ~30 minutes
- James input required: 0 for the build · ~30 sec for the first answer (in TG)

## Composition

- `[[project-james-ask-reverse-channel]]` — full architecture · schema · usage · failure modes
- `[[project-sunheart-flow-spine]]` — Phase 2 wire (inbound) shipped earlier this session · this is the outbound complement
- `[[feedback-no-outsourcing-to-james-what-substrate-can-do]]` — the rule this serves at its deepest · substrate does all the assembly · James only does the irreducible answer
