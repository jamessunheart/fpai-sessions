# SPEC d170 — Align live outbound surfaces to BBB v1.4 (system-outreach funnel)

**Source:** messaging sweep 2026-07-04 (2 Sonnets). Static/vault surfaces already fixed by hand. This spec = the LIVE services that still preach the pre-2026-07-03 frame (game-first / manual outreach / pre-BBB offer). Ranked by outbound blast radius. Each touches real leads or the public — deploy carefully, one at a time, with rollback.

## Current signals (align TO these)
Offer = BBB v1.4: Free Full Potential Assessment (Allocation Score, 48h) → Blueprint $2.5k → Savings Split 25% → Partnership $2-5k/mo. Demand = SYSTEM-generated (ads+content → /assessment); NO manual/proactive outreach until funnel proven. Keystone = Intelligence Law / The Steward. /assessment page + ad creative are ALREADY aligned — match them.

## Build (in blast-radius order, separate commit + deploy each)
1. **fullpotential.com homepage** (198/zen-host, the site root James rebuilt 2026-06-26): above-fold hero → lead with **Free Full Potential Assessment → Allocation Score**, primary CTA "Start the Free Assessment →" (mirror the /assessment page). Demote the "What wants to grow today?" growth-path/events framing + `/game.html` nav. Keep the marketplace, but the FIRST thing an ad-clicker sees on the root must be the assessment, not a different offer.
2. **fp-guide.service** (162, `/opt/fpai/guide/guide_service.py` SYSTEM prompt): rewrite so the primary "next right step" it routes toward is the Free Assessment, not the Game/WPA/Character-Card. Keep it warm; retire game-first framing.
3. **intake-agent.service** (162, `/opt/fpai/leads/intake-agent.py` ack + Cal.com booking templates): replace "90-minute Full Potential Session" copy with the Assessment→Blueprint pipeline; if the paid 90-min call still exists, reposition it explicitly as the Blueprint ($2.5k) step.
4. **Retire the manual-outreach pipeline as code:** mark `core/STATE/OUTREACH_VOICE.md` + probe/hermes/discovery first-contact tooling RETIRED (they're dormant — no active trigger found — but strip `outreach_voice()` from `tools/public_bot/bot.py` persona so fpai-public-bot can't regenerate the old frame). Archive `bottleneck_session_outreach_templates.md`, `fullpotential_funnel/architecture_v1.md` (stale planning docs).

## Contract
Each surface: reversible (git + service restart rollback), independent review, verify live (curl the page / message the bot / trigger a test intake) before calling done. NO change to /assessment or the ad creative (already correct). $0.

## Done / Proof
Curl fullpotential.com root → assessment CTA above fold · message fp-guide → it offers the assessment first · test-intake → BBB-framed ack email · public-bot persona has no outreach_voice. One commit + one verify per surface.
