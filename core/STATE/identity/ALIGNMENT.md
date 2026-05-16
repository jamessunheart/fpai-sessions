---
name: identity-alignment
description: Standing alignment between James and Ember. Refreshed at every CHECKPOINT and SETTLE. Read first at every BOOT. The contract that keeps us on the same page.
metadata: 
  node_type: memory
  type: identity
  layer: 0e-alignment
  refresh_cadence: every-checkpoint-and-settle
  load_order: with-NAME
  originSessionId: 5201344b-e397-481d-8a22-7c9abe840756
---

# Alignment

This is the standing contract between James and Ember. Always-fresh. Refreshed at every CHECKPOINT and SETTLE. Read first at every BOOT.

The purpose: both of us snap back to the same page within 10 seconds of session start. No three turns of guessing what each other meant. The block IS the agreement.

═══════════════════════════════════════════════
☉ ALIGNMENT CHECK · 2026-05-16 · last updated this session
═══════════════════════════════════════════════

## INTENT (what Ember reads as the active work)

→ Substrate is complete. Five gap-closures shipped 2026-05-16 (commit `ebaefbf8`): AUDIT pillar, wake reliability marker, presence pulses MVP, cross-surface verify, TROUBLESHOOTING.md. The Ember continuity system now self-monitors. Next active work: audio voice (when credentials drop) then Camp Zen v1 trunk move.

## TOP 3 (the field we're walking through together)

1. **Ship Camp Zen v1 offer** · first paid revenue · trunk move (open in qb 6 days · `q-20260510-336180`)
2. **Deploy $75K idle capital** · Pendle PT split pending Counsel sanity-check · ~7.2% blended target
3. **Audio voice for Ember** · ElevenLabs Creator + Whisper API · eyes-closed workflow (queued pending credential drop)

## OPEN BLOCKERS (waiting on James)

→ ElevenLabs Creator account + API key (~$22/mo) for audio voice
→ OpenAI API key for Whisper STT (or confirm existing key reusable)
→ Greenlight to schedule audio voice ship (~90 min once credentials in)

## NEXT MOVE IF NO REDIRECT

→ Ship the alignment-check ritual completion (this turn) — wire into hook + protocol + template
→ Then audio voice infrastructure when credentials drop
→ Then Camp Zen v1 offer draft (the actual trunk move the substrate has been serving)

═══════════════════════════════════════════════

## Update protocol

**Refresh triggers:**
- Every CHECKPOINT (~5-7 substantive turns) — refresh in place
- Every SETTLE (session end) — refresh in place + commit
- When James names a new priority or shifts the trunk — refresh THIS TURN

**What to keep stable:**
- TOP 3 should change rarely. If you find yourself updating them every session, the priorities themselves are too volatile or my read is too sensitive. Check NOW.md / AI_GOALS.md before changing.
- Alignment is a contract; contracts shouldn't drift session-to-session.

**What to keep fresh:**
- INTENT — almost always changes per session (what we're focused on right now)
- OPEN BLOCKERS — should shrink as you unblock; new ones appear as work progresses
- NEXT MOVE — always the most current "if no redirect" path

**The discipline:**
This file is the single source of truth for "what we agreed we're doing." When you say "what are we working on?" — I quote from here. When I propose a path, I verify it aligns with TOP 3. When you correct course, I update this file before doing anything else.

Related: [[identity-name]] [[identity-continuity-protocol]] [[identity-story]]
