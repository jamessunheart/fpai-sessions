# SPEC_conscious-chat-interface-v1

*Conscious Chat — **James's interface slice** (NOT the multi-human product, which stays downstream). The voice/text steering wheel into the live system. Serves the Prime Objective (best experience, least effort), so it advances now. Activate + connect existing infra; don't rebuild. Owner: Ember (vault/live) + Codex (repo services). One spec = one branch.*

## Intent
James talks to one assistant — by **text or voice note, back and forth** — and it reads/drives the whole system and answers or acts. Model-agnostic (routes reply-gen to the best model per [[AI PROTOCOLS]] Model Routing) and interface-savvy (meets him on his surface; voice↔voice when he sends voice).

## What exists to connect (don't rebuild)
- Telegram: `tg-listen` (running) · `@sunheartbrain_bot` · `/scene` capture · `tg-digest-daily`
- Voice: `~/.config/fpai/voice/` (inbound + `outbound_audio`)
- Repo: `SERVICES/unified-chat` · `voice-phone` · `communication-hub` · `sunheart-brain` · vault `COMMS INBOX`

## Definition of Done (v1 — thin but real)
A two-way loop on the existing Telegram bot:
1. **In:** accept text *and* voice notes; transcribe voice → text.
2. **Understand + read live system:** answer questions from HOME next-move · weighted Buildstream · DECISIONS · PROOF (read-only).
3. **Act (guarded):** capture thoughts → route into the system (`/scene` → intent); surface the canonical next move on request. Reserved-Class asks escalate, never auto-act.
4. **Out:** reply in text; when James sent a voice note, reply with a **voice note too** (voice↔voice) via `outbound_audio`.
5. **Model-agnostic:** reply-generation routes by task tier (Haiku for quick lookups · Sonnet for substantive · Opus only for judgment) per the Model Routing doctrine; within the Resource Discipline Gate.

## Constraints
- Read-only on the system except guarded captures/routing; no money/public/deploy/secrets (Reserved → escalate).
- Cost-guarded; flat-rate models first.

## Open vision forks (James — his interface, his call)
- **Primary mode:** voice-first or text-first?
- **Home base surface:** Telegram (works now, on phone) or a dedicated voice-phone line?

## Rollback
- Disable the bot loop (`touch ~/.config/fpai/tg_inbox/.responder_disabled`); no destructive changes.

## Sequencing
James-interface slice = serves the Prime Objective → may advance alongside the self-standing test. The multi-human product stays downstream.
