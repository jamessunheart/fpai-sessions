# SPEC d177 — TG bot: clean, voice-first, self-aware, and able to ACT (not just chat)

**Goal (James 2026-07-04):** "a clean, clear, smart and capable Telegram bot I can send voice memos to, aware of its capabilities." Root model bug already fixed (d174: was silently on llama3.2:3b, now Sonnet). This closes the rest. Code: `/opt/sh-brain-src/curator/tgbot.py` (service `sh-brain-tgbot`) — deploy there, test live, one commit per part.

## Part 1 — Kill the noise (unsolicited pushers → one digest + real events)
Audit confirmed pushers to James's chat (8514069423): `fpai-morning-digest.timer` (05:00 UTC), `zv-morning-digest.timer` (13:00 UTC — Zen Village, likely wrong channel), `cora-loop/kai_bridge.py` + `triad_bridge.py` (loop status), `leads/lead-capture-api.py` (WANTED — lead events).
- Inventory EVERY service that can `sendMessage` to James's chat (grep list in the session). For each: keep / reroute to its own channel / kill.
- Collapse to: **ONE morning digest** (money · decisions · what built overnight · leads · anomalies) + **event-only alerts** (lead in · build merged/failed · spend>cap · model-degrade). Kill zv-digest to James (send to a ZV channel or off). Silence cora-loop intermediate status.
- Rule: every push must earn its interruption. Quiet hours 22:00–07:00 CR batch to morning (except failures/leads).

## Part 2 — Voice-first (already transcribes; make it the primary lane)
Bot already does voice-in via OpenAI Whisper (`_transcribe_voice`) + voice-out toggle. Harden: confirm the Whisper path is healthy end-to-end; make voice memo the first-class input — transcript shown briefly, then acted on. On a long voice memo, the bot should (a) capture it, (b) detect intent (question / decision / build-request / journal), (c) route accordingly (see Part 4).

## Part 3 — Capability self-awareness (honest self-model)
The system prompt must state truthfully what the bot CAN and CANNOT do (P4 honesty; today it over-claims). Bot CAN: chat on Sonnet, cross-conversation memory, transcribe voice, search the brain, capture to Linear, report live system state, run ~20 slash commands, QUEUE actions. Bot CANNOT (route these to terminal-Ember/the loop): execute bash/git/ssh, edit files, deploy, run agents/workflows, move money. A `/whatcanyoudo` command returns the honest capability list. Never claim an ability it lacks; when asked to DO something it can't, it says "queuing that for the builder" and actually queues it (Part 4).

## Part 4 — The ACT bridge (voice memo → real action, the "capable" part)
Today a voice memo → chat reply or Linear note. Add: when James's message is an intent to build/change/decide, the bot writes it into the SAME queue the terminal uses — insert a `brain_index.decisions` row (needs_build for a build; captured for a decision) or drop a `core/BUILD/specs/SPEC_*.md`, so his voice memo becomes a queued build the loop picks up. Confirm back with the dNNN id + ETA (ties to d155 alerts). This turns the bot from a mouth into hands-by-proxy without needing full Claude Code.

## Contract
$0 (Sonnet via Max + Whisper minimal) · reversible per part (code revert + timer re-enable) · independent review · test live each part (send a voice memo → see it captured, intent-routed, and if a build-request, a dNNN queued). NO change that can move money or self-merge.

## Done / Proof
Send a voice memo "build X" → bot transcribes, replies Sonnet-grade, queues dNNN, confirms with ETA · `/whatcanyoudo` returns honest list · only ONE morning digest + event alerts arrive over 24h (no random pushes) · forced model-degrade fires a loud alert (d174).
