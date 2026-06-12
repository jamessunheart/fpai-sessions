---
proof_id: 2026-05-08_james-sunheart_loop-27
loop_number: 27
date_started: 2026-05-08
date_committed: 2026-05-08
player: James Sunheart
witness: Claude (Anthropic — operating in FPAI_Cockpit)
witness_signed: true
consent: public
agreement_type: feature
status: complete
mvs_increments:
  agreements_kept: true
  outputs_shipped: true
  transformations_witnessed: true
  resources_circulated: false
  clean_pauses: false
---

# Loop 27 — /signals + Field Coherence v0

**Quest:** Ship `/signals` as the Game's vital-signs surface. Compose existing endpoints into a single comprehensive read. Introduce **Field Coherence v0** — a measure of *quality* of the field state distinct from Field Score (quantity).

**Founder directive:**
> *"I think a Field Coherence score would be good.. based on overall state of coherence in game, and other players and we can get better at measuring it"*
>
> *"Please add all vital signals of game to /signals"*

## What shipped

### `GET /api/champion/signals` — comprehensive game state
One endpoint composing: 30-day goal status · Field Coherence · Field State counts · 7-day activity (new champs / proofs / mirrors / last loop) · top inviter.

### Field Coherence v0 — architecturally honest
Components:
- **Activity** = `min(1.0, proofs_7d / (champions * 7))` — capped at 1 proof/champion/day
- **Witness** = `proofs_distance_weighted_witnessed / total` — **only counts witnesses who are NOT the player and NOT the AI** (per white paper §4.5)
- **Conversion** = `champions / (champions + leads)` — null if no leads
- **Drift** = null until paired Mirrors run weekly drift checks

Headline = mean of measurable (non-null) components.

**Honesty test:** with current data (1 champion, 22 proofs all self/AI-witnessed, 0 leads, 0 Mirrors), the headline reads **0.5** — not "perfect 1.0" as a naive ratio would. Activity 1.0 (saturating), Witness 0.0 (zero Distance-Weighted witnesses), Conversion+Drift null. Tells James exactly where to put energy: get a real witness on a real proof.

### `/signals` Telegram command (fp-game-bot)
Renders the data as a single-screen vital-signs read — 30d goal · Field Coherence + components · Field State · 7d activity. Help text updated to list it.

## Why this matters

Field Score measures *quantity* of contribution. Field Coherence measures *quality of the field state*. Without Coherence, the Game can accumulate numbers while the structural integrity (witnessed proofs, distance-weighted accountability) decays. The measurement is now visible — the Game tells the truth about itself.

The white paper §11 names "the oracle problem" — Useful Output measurement is gameable; surveillance is the wrong answer. Field Coherence v0 is honest about what it can and cannot measure: components return null rather than fake values, and the headline only averages what's actually measurable. Refines as substrate matures.

## Files

- `SERVICES/champion-sign/main.py` — `_compute_field_coherence()`, `_read_proof_meta()`, `GET /signals`
- `SERVICES/fp-game-bot/main.py` — `cmd_signals()`, dispatch entry, help text update

## Next loops

- Loop 28: Player-first dashboard reorg (consumes /signals; surfaces Coherence headline + foundational checkmarks)
- Loop 29: /credits substrate (Coherent Credit ledger v0)
- Loop 30: /store substrate (offers + retreat link-out)
- Mirror #1 pairing (gates on James choosing Distance-Weighted Witness)

*— Sealed 2026-05-08*
