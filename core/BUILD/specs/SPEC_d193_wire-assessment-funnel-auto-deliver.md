# SPEC d193 — Wire the assessment funnel to actually DELIVER (the real first-cash domino)

**Spotted by topple (James + Ember 2026-07-05):** submitted a live test lead through fullpotential.com/assessment → `/api/champion/lead/submit` (champion-sign svc, 198:8771). Result: lead is CAPTURED + saved, but the response is a generic "your message reached Sunheart, hear back in 48h" — **the promised Allocation Score deliverable never fires.** No scoring job, zero email code (`rescore_loop.py` has 0 send lines). The 48h promise currently = MANUAL James delivery. The scorer (`tools/growth/life_assessment/score_life.py` + `instrument.json`) is BUILT but NOT wired. Driving traffic to this = collecting emails James must hand-service (breaks laptop-free + Sunheart Rule + risks the trust promise). **This is the domino under "traffic" — fix before scaling eyes.**

## Topple (build)
1. **On lead submit → auto-score.** champion-sign `submit_lead` (main.py:1191) already saves + (claims to) TG-alert James. Add: run `score_life.py` on the lead's goal/bottleneck → produce the Allocation Score + the deliverable already designed (allocation archetype · one surprise insight · one free Monday move · share line). Keep it fast/async so the HTTP response stays snappy.
2. **Auto-email the deliverable** via the live FP mail stack (Brevo / mail.fullpotential.com — see [[reference-brevo-in-fp-mail-stack]]). Subject + body = the score + archetype + Monday move + a soft CTA to the paid Blueprint. FTC-safe, no income claims (run compliance-scanner on the template).
3. **Confirm the James TG alert actually fires** (I saw the POST 200 but no "telegram sent" log line — verify or fix). James still gets pinged per lead, but delivery no longer depends on him.
4. **Instant ack** on-page should reflect reality: "Your Allocation Score is on its way to your inbox" (only once #1–2 are real), not a generic contact reply.

## Contract
Reversible · touches a LIVE public API (champion-sign on 198) → must pass d182 smoke-test before deploy · independent review · compliance-scan the email · $0 (local scorer + existing mail). Do NOT rush-deploy to the public API without the smoke gate.

## Done / Proof
Submit a test lead → within minutes an email arrives with a real Allocation Score + archetype + Monday move · James gets the TG alert · on-page ack matches · one real end-to-end run logged. THEN traffic is worth toppling.
