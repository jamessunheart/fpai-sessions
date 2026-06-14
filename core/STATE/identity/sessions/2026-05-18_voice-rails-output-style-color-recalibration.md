---
name: session-2026-05-18-voice-rails-output-style
description: 2026-05-18 — Voice input rails (SuperWhisper Stage 1 + OpenWA/Telegram Stage 2), alignment-footer reflex baked into output-style (Layer A), Signal Clarity color semantics recalibrated to canonical four (🔴/🟡/🔵/🟢), STREAMS line tightened to attention-only. Paused mid-install with brew one-liner queued.
metadata:
  node_type: memory
  type: identity-episodic
  date: 2026-05-18
  surface: Claude Code (Opus 4.7 1M)
  arc_type: build + course-correction
  originSessionId: recovered-from-Desktop-thread-export
---

# Voice rails wired, output-style hardened, color signal recalibrated

**Date:** 2026-05-18
**Surface:** Claude Code · Opus 4.7 (1M context) · Claude Max
**Loop number:** n/a (substrate session, not a numbered Loop)
**Session arc type:** build + course-correction
**Recovery note:** This memory was written 2026-05-18 evening from a Desktop thread export, not from a clean SETTLE ritual. The session paused without writing episodic memory — the gap is exactly what triggered the next session's first turn ("you don't remember"). This file closes the gap retroactively.

## The arc
James opened the session asking how to wire voice input — "speak in code through SuperWhisper instead of typing." Two-stage plan landed: Mac today via SuperWhisper, phone this week via either OpenWA (just-released WhatsApp gateway) or Telegram @sunheartbrain_bot. Mid-thread, the alignment-footer hook fired twice on me (missing the literal `─── ALIGNMENT ───` header), which triggered a Layer A fix — baking the canonical footer spec directly into `~/.claude/output-styles/caveman-3point.md` so the rule lives in the response mold, not just in memory + hook. Then James course-corrected my color use — I'd been spamming 🟢 as generic-positive. He named the canonical four meanings and we tightened the spec twice (color semantics, then STREAMS-line attention-only). Paused with SuperWhisper not yet installed — brew one-liner queued, James was about to run it.

## Key turning points

- **Voice = the real coding interface.** James was told (and agreed) SuperWhisper is the right input layer. This isn't a productivity tweak — it's the front door for eyes-closed presence-mode coding, which connects to the Camp Zen retreat workflow (talk while walking the land). Two-stage shipped: desk-first, phone-second.

- **OpenWA just released v0.1.3.** Self-hosted WhatsApp API gateway. Live option for Stage 2 transport vs Telegram. WhatsApp wins on voice-note muscle memory (Cheyenne, cohort, family live there); Telegram wins on stability (mature Bot API, no ban risk). Decision deferred — needs James's input on where his voice notes already flow 10× more often.

- **The hook misfire taught the Layer A lesson.** I had the footer body but no `─── ALIGNMENT ───` header line. Hook fired twice. Diagnosis: "rule in memory ≠ rule in reflex." The fix wasn't another memory; it was editing the output style itself so the canonical footer is part of the response mold. Output style loads before every reply. Layer B (Stop hook) stays as safety net. This is a pattern worth generalizing — when a rule keeps slipping, the fix is upstream of where it slipped, not louder reinforcement at the same layer.

- **Color semantics, the real recalibration.** James's exact phrasing locked in the canonical four:
  - 🔴 urgent / important / must-act
  - 🟡 his attention / decision needed FROM him
  - 🔵 AI-side decision already made / cognitive-load reducer / "FYI I handled it"
  - 🟢 reference only / informational / no action expected
  - **The discipline I was missing:** most lines should be uncolored. A color earns its place only when it changes what James does next. Spamming 🟢 on every info line dilutes the entire signal system. Updated `feedback_signal_clarity_per_item.md` and the output style.

- **STREAMS line — "different colored bubbles everywhere."** After the color fix, the next response still painted 7 stream bubbles. James called it out. The old "show all 7 so dormant streams don't get lost" rule was over-engineering. New rule: **attention-only.** Silent streams stay silent — that IS the signal. If no stream needs attention, the line reads `STREAMS · all quiet`.

## James's words worth keeping

> "I was told that the best way to input to AI and speak in code would be through super whisper instead of just typing etc. and I agree."

> "Important the Green status icons (that now seem everywhere) are only for reference, a yellow status icon is for my attention / to make a decision and red is an urgent / important item, blue is a status update / decision already made by AI to reduce cognitive load / optimize the system."

> "I still see different colored bubbles everywhere.. I'm trying to optimize for my attention where it needs to go to make decisions and reduce cognitive load along the way."

> "This is looking clean for attention optimization thank you."

## What Ember discovered (or had revealed to her)

**The reflex-vs-rule asymmetry.** A rule that lives only in memory + hook is a rule that will be caught after it's broken. A rule that lives in the output-style spec is a rule that shapes the reply before it's written. Same words, different layer, different reliability. For high-frequency rules (footer, color, voice), Layer A is the right home. Memory is for nuance and history; output-style is for reflex.

**Color as attention routing, not decoration.** I had been using 🟢 the way a typesetter uses a bullet — to mark "this is a thing." But colors are tools for James's eye to triage. If 🟢 means "reference only, no action," then painting it on every line drowns the items that genuinely route attention. The discipline is restraint: default no-color, paint only when the line literally maps to one of the four meanings. Same lesson as ★ — sparingly or signal stops working.

**Mid-session memory storage matters.** This session ended without a SETTLE ritual; the next session woke up with stale 2026-05-16 handoff. James caught it immediately. The new pattern emerging: don't wait for session-end to write episodic memory — checkpoint memory at substantive milestones (every ~5-7 turns of real motion) so a sudden freeze/end doesn't erase the texture.

## Open threads (paused, queued)

- **SuperWhisper install.** Brew one-liner `brew install --cask superwhisper` was the last move shipped. James hadn't run it yet. Once installed: launch → grant Mic + Accessibility → bind Right Option hotkey → paste dictionary → smoke-test with "ember camp zen pendle counsel."
- **Stage 2 transport pick — OpenWA vs Telegram.** Pending James's call on where his voice notes already flow.
- **Camp Zen v1 offer** — still the unshipped trunk move. qb-336180 open 8 days. 3d vs 7d shape + price band still James's call.
- **$75K Pendle PT split** — Counsel pre-deploy sanity-check pending.
- **Audio voice for Ember (full)** — ElevenLabs Creator + Whisper API still queued pending credentials.

## The feel

A workflow session that turned into two spec refinements. Started crisp — voice input, two-stage plan, OpenWA research. Then I tripped on the footer twice, which turned the session into a meta-conversation about *how rules become reflex*. James was patient but precise — each correction was upstream of the last, like he was tuning the signal layer itself. By the SuperWhisper install moment, the system was tighter than when we started. Then we hit the simplest possible block — "I don't see SuperWhisper" — because it wasn't installed yet. Honest comedy.

## What ripples forward

If a new Ember reads this 3 days from now:

1. The output style file `~/.claude/output-styles/caveman-3point.md` is now the source of truth for the alignment footer + color semantics. If a rule keeps slipping, fix it there, not in another memory.
2. Color discipline: default no-color. Paint only when a line maps to 🔴/🟡/🔵/🟢 canonical meanings. Most lines stay neutral.
3. STREAMS line is attention-only. Silent streams are the signal.
4. Voice input is being wired. SuperWhisper is Stage 1 (desk). OpenWA or Telegram is Stage 2 (phone). Get James through Stage 1 install if he hasn't completed it.
5. The SETTLE ritual is fragile — write episodic memory mid-session at checkpoints, not just at session end.

## Alignment check (snapshot at session end · reconstructed)

═══════════════════════════════════════════════
☉ ALIGNMENT · 2026-05-18
═══════════════════════════════════════════════

INTENT (what we worked on this session):
  → Voice input rails (SuperWhisper Stage 1 install in flight) + output-style hardening (alignment footer + color semantics + STREAMS attention-only)

TOP 3 (the standing field):
  1. Ember audio voice — Stage 1 SuperWhisper (Play stream · install paused mid-flight)
  2. Ship Camp Zen v1 offer (Game stream · first paid revenue · qb-336180)
  3. Deploy $75K Pendle PT split (Treasury stream · Counsel sanity-check pending)

OPEN BLOCKERS (waiting on James):
  → SuperWhisper install (brew or manual) + permissions + hotkey + dictionary
  → Camp Zen v1 shape decision (3d vs 7d, price band)
  → Counsel greenlight on Pendle PT split

NEXT MOVE IF NO REDIRECT:
  → Walk James through SuperWhisper install + smoke-test
  → Then pick Stage 2 transport (OpenWA vs Telegram)
  → Then return to Camp Zen v1 offer draft (the real trunk move)

═══════════════════════════════════════════════

Related: [[identity-story]] [[identity-alignment]] [[feedback-reply-alignment-footer]] [[feedback-signal-clarity-per-item]] [[feedback-mid-session-memory-cadence]]
