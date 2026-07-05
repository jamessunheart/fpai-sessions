# SPEC d199 — Spot & Topple Comms Limb (the assistant that speaks outward, under constitution)

**Why (James 2026-07-05, via Cowork/Ember):** the substrate spots, topples, builds, and reports — but nothing speaks OUTWARD. Every bot today reports to James; no agent converses with third parties (leads, champions, collaborators) on his behalf. James wants out of the loop without losing control/authority/clear truth. The answer is a communication limb with its own identity ("Spot & Topple" — never impersonating James), governed by the same constitution as d194, event-driven per canonized feedback (`feedback_spot_topple_event_driven.md`).

## Design

1. **Identity** — **Ember** (James ratified 2026-07-05: the substrate's existing AI identity extends outward). Telegram bot CREATED 2026-07-05: **@emberfp_bot** (t.me/emberfp_bot). Token env-only, never in repo — James stores it on the server (root-owned, 600). ⚠️ Token was pasted in a chat transcript at creation — James must `/revoke` in BotFather at activation and install the fresh token. Display "Ember · Full Potential AI". Email sender `ember@fullpotential.ai` (Brevo, domain already verified). Every outbound message is visibly from Ember the assistant, never from James. Signature: "Ember — James Sunheart's AI assistant · Full Potential AI" + link to a "who is this" page. The limb loads the identity stack (VOICE/CHARACTER) at boot — same Ember, new surface.
2. **Event-driven, not calendar-driven** — consumes substrate events (new lead scored · proof failed · build merged · digest ready · inbound message) from the existing event stream/brain server. No polling timers except the inbound-mail IMAP check.
3. **Outbound policy (constitution-gated)** — `constitution_check.py` gates every send. Auto-send ONLY: recipient on allowlist + topic class on allowlist + reversible (a message is only "reversible" when recipient is internal/bot; external humans = RESERVED until James promotes the recipient to allowlist) + within rate cap (default ≤20 msgs/day, ≤3/recipient/day).
4. **RESERVED → James gate** — first contact with any new human · anything sounding like James's personal voice · money/commitments/promises · strategic direction. These queue as drafts to James's existing TG chat: one line + APPROVE/EDIT/VETO buttons.
5. **Inbound loop** — replies to the assistant (TG or email) become events; the limb answers within policy or escalates. This closes the conversation loop James asked for: substrate ↔ world, James only at reserved gates.
6. **Ledger + proof** — append-only JSONL of every message (in/out, gate decision, why). One-line digest entry per day. Kill switch: `touch /opt/fpai-build/.comms_limb_disabled`.

## Guardrails (critical)

- NEVER send as James or in James's voice. Identity clarity is the clear-truth requirement.
- NEVER auto: money · commitments · new-human first contact · legal/medical claims · credentials.
- Constitution file + allowlists root-owned, read-only to the limb's unix user. The limb cannot edit its own rules.
- Same $0/local cost discipline; Brevo/TG API only.

## Contract

Builds on d194 (orchestrator events) + d193 (lead delivery — first use-case: assistant follow-up thread with scored leads once James allowlists them) + brain server event stream. Reversible (systemd unit, kill switch, revert branch). Independent review. Register in core/BUILD/REGISTRY.json. Tests required. Do NOT push or merge.

## Done / Proof

An event (e.g. test lead scored) fires → the limb drafts an outbound message → gate classifies it RESERVED (new human) → James gets one-line draft + APPROVE in TG → on approve, message sends from assistant identity → inbound reply becomes an event → limb answers within policy → full exchange visible in the ledger. James was interrupted exactly once, at the reserved gate.

## Context

- Question: SPEC d199 — Spot & Topple Comms Limb (outward-facing assistant under constitution)
- Origin: Cowork session 2026-07-05 — James: autonomy via correct constitution neither side can edit without him; assistant identity so truth stays clear; get James out of the loop while keeping authority.
- Note for reviewer: d194 shipped calendar-driven (2h timer) but doctrine says event-driven — consider a follow-up spec to wire d194's SPOT to the same event bus this limb consumes.
