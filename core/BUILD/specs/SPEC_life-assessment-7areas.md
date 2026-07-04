# SPEC — Life-lens Assessment: wire the 7-Areas instrument (Life track spine)

Doctrine: `core/STATE/ACADEMY/ACADEMY_PATTERN.md` — **ONE Assessment front door, two lenses.** Business lens exists (`tools/growth/score_assessment.py`). The Life lens core is **already built and proven**: `tools/growth/life_assessment/instrument.json` (21 questions, 7 areas) + `score_life.py` (Allocation Score 0-100, mean-of-means ×10, lowest area = practice target; `--demo` passes). This spec wires it to humans.

## Build (in order)

1. **Web intake** — add the life lens to the existing /assessment funnel: a "business or life?" routing question at the top; life path renders the 21 questions (2 sliders + 1 short-answer per area) and POSTs to the same lead pipeline the business lens uses. Compute score server-side (or client-side then verify) with `score_life.py` logic — do NOT fork the math, import it. Render the deliverable (score, area bars, practice target, their named AIM) on the thank-you page + into the lead email James receives.
2. **Ember re-score loop** — daily voice-note/text check-in → classify to one of the 7 areas → bounded ±1 nudge (floor 0 / ceiling 10, max 1/area/day) on a per-person running score (state file per participant under `~/.config/fpai/life_assessment/` or DB row). Formal instrument only at Day 0 + Day 14; the D0→D14 delta is the reportable metric. Surface conversationally, never a chart.
3. **Admin view** — internal-only JSON/CSV: cohort Day-0 vs Day-14 deltas per area (feeds funnel proof-content).

## Contract
$0 path (subscription/model_router, same as assessment-scorer). Reversible: new files + additive route only — never touch the live business-lens A/B test. Independent review before merge. Register heartbeat.

## Done / Proof
One human completes the life intake on the web → gets their Allocation Score + practice target → the lead lands with the score attached. Demo delta run (Day 0 vs Day 14 fixture) renders in the admin view.

## Reserved (James)
Cohort-1 roster + launch date. Everything else buildable now.
