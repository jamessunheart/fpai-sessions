# SPEC_d133 — Public learning interface (the one-chat, pointed outward)

Authored by Ember, 2026-06-30. Corrects a priority error: we specced outreach (d069–d072) before
building the destination outreach drives people to. A stranger currently has NO live conversational
surface to interact with the system — so the value conversions (VPI/VCR in `LEARNING_METRICS.md`) have
no possible input. This builds the destination. It is the TRUE highest-leverage move (the weakest
conversion is Reality / no users), and it must exist BEFORE `OUTREACH_LIVE=1` is meaningful.

## Build

Extend the proven internal one-chat pattern (`sh-brain-tgbot`, server 162) to a PUBLIC, stranger-safe
surface on `@sunheartai_bot` (public bot, creds already at `~/.config/fpai/tg_sunheartai/`). Reuse,
don't rebuild — the chat synthesis, brain_index, and privacy rails already exist.

1. **Public chat service** on `@sunheartai_bot`: a stranger messages → Ember responds with real value
   (full-potential guidance / the Game on-ramp). Reuse the existing synthesis engine but with a
   PUBLIC system prompt (no private state, no James-internal context).
2. **Public-context guard**: every response is built through the EXISTING `tools/privacy/public_context_pack.py`
   + `canary_probe.py` so no private/internal data can leak into a public reply. Hard gate.
3. **Learning capture (the point)**: each public conversation logs to `brain_index` as a learning row
   tagged `tier=PUBLIC, source=public_chat`, with explicit consent on first contact ("conversations
   help improve the system — ok?"). These rows are the raw input for VPI (did the person benefit?) and
   feed the d129 outcome signal + the Academy.
4. **Engagement signal**: write `probe_session`-style rows (engaged=true/false, benefit-signal) so the
   conversion ledger (d132) can finally populate VPI instead of `unknown`.

## Context — why this is THE priority

The three flywheel diagrams all converge on one law: get real-world data, optimize the weakest
conversion. Our weakest conversion is Intelligence→Value, starved because no external human is on the
receiving end. The internal one-chat proves the pattern works; this points it at the world. Outreach
(d069–d072) becomes useful ONLY once this destination is live — otherwise outreach sends people nowhere.

## Honest constraints (load-bearing)
- 🔴 OUTWARD-FACING — touches real strangers + their data. Privacy is non-negotiable: public_context_pack
  guard + explicit consent + default PRIVATE for anything sensitive (`Privacy Tiers`, privacy-narrator).
- 🔴 Honesty rule from the one-chat carries over: the public bot NEVER claims a capability it doesn't have
  (the 2026-06-14 confabulation fix). It says plainly what it can/can't do.
- 🟡 Launch SMALL: soft-launch to a tiny invited cohort first (first-cohort / Champions), measure VPI on
  real conversations, THEN open + turn on outreach. No mass-blast before the destination is proven.
- 🟡 James gates the public go-live + any outreach that drives volume (outward-facing decision).

## Contract
Follow `docs/codex/SESSION_CONTRACT.md`. Branch off `feat/headless-build` (never main).
Register in `core/BUILD/REGISTRY.json` (status building->done). Tests required (public-context-pack
leak tests MUST pass; assert no private block reaches a public reply). Do NOT push, deploy the public
bot, or open PRs — Ember merges after independent AI review; James gates the live public turn-on.

## Done / Proof
independent-AI-reviewed branch with: public chat service wired to `@sunheartai_bot` (behind a
`PUBLIC_CHAT_LIVE=0` flag, OFF by default), passing public-context leak tests, consent-on-first-contact,
and learning-capture writing `tier=PUBLIC` rows + engagement signal. Soft-launch checklist for James.
Ready for merge; live turn-on is James's gated call.
