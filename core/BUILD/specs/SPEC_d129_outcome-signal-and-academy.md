# SPEC_d129 — Outcome signal + The Academy (close Feedback→Learning)

Authored by Ember from the Learning-Flywheel synthesis (James + GPT, 2026-06-30). Closes the one
remaining break in the Feedback→Learning loop the scout identified: the system measures whether a
build shipped, runs, and matches intent — but never whether it **improved an actual outcome**. Then
it adds the missing organ: a distiller that turns measured experience into reusable curriculum.

## Build

Two parts, small blast radius, experiment-lane only (NO autonomous prod deploy — that stays gated).

**Part A — Outcome signal (the missing measurement).**
- Add an ops_ledger signal type `feature_outcome` (alongside existing `loop_run`, `liveness:pass/fail`, `horizon_scan`).
- Each merged+activated spec gets ONE outcome row written after a measurement window: `{spec_id, metric_name, baseline, observed, delta, verdict: improved|flat|regressed|unknown}`.
- Source the metric from whatever the spec declared it would move (add an optional `## Outcome metric` field to the spec template; if absent, verdict=`unknown` and that itself is a logged signal — "we shipped something unmeasurable").
- Wire it into `tools/learn/session_feedback_seed.py` (currently lines ~84-98 read REGISTRY/reviews/corrections but have NO runtime-quality reader) and `tools/learning/dataset_builder.py` (export `feature_outcome` rows as training signal, not just corrections + merge outcomes).

**Part B — The Academy (distill experience → curriculum).**
- New tool `tools/academy/distill.py`. Reads: proofs (`core/INTENT/AGREEMENTS/proofs/`), `brain_index.corrections`, the new `feature_outcome` rows, `docs/codex/CONSEQUENCE_REPORT.md`.
- Emits ONE durable curriculum file `core/STATE/ACADEMY.md` (git-tracked, bounded) with three sections:
  - **Principles** — patterns that repeatedly produced `verdict=improved`.
  - **Cautions** — patterns that produced `regressed` or drew James corrections.
  - **Playbooks** — repeated successful sequences, named + reusable.
- The system reads `ACADEMY.md` on boot (add to the Layer-1 canonical reads in CLAUDE.md once proven).
- Nightly cron entry (launchd, staged in repo for James to load — persistence is gated): run distill after the build loop settles.

## Context — why this and not more agents

We already have ~90% of the learning architecture (Loop, Council, Forge, Ledger, liveness probe,
consequence watcher, correction capture, dataset builder). We do NOT need new agents. We need (1) the
outcome signal that tells learning whether decisions actually worked, and (2) the distillation step
that converts raw experience into reusable knowledge. Accumulation ≠ learning. 1,511 stored resources,
zero curriculum.

The objective-function shift underneath: stop optimizing awareness % (a snapshot). Start optimizing
**improvement-velocity** (the derivative). `feature_outcome` deltas are the raw material for that metric.

## Follow-on (NOT this spec — keep blast radius small)
- **d130 — Curiosity engine:** repoint qb introspective. Nightly generator asks "what assumption am I wrong about? where am I uncertain?" → opens qb questions → feeds the build queue.
- **d131 — Metabolism:** nightly "improve ONE thing about yourself" cron wiring recursive-optimizer → forge → Ledger, experiment-lane, deploy-gated.

## Honest constraints (load-bearing)
- 🔴 NO autonomous prod deploy. The metabolism/outcome loop runs in the experiment/proof lane and SURFACES wins for the human/council merge gate. The harness hard-blocks self-escalation; this spec respects that.
- 🟡 Guard against learning-for-its-own-sake. Every Academy principle must trace to a `feature_outcome` or Ledger delta — no principle without evidence. Distillation toward value, not vibes.

## Contract
Follow `docs/codex/SESSION_CONTRACT.md`. Branch off `feat/headless-build` (never main).
Register in `core/BUILD/REGISTRY.json` (status building->done). Tests required (unit-test the
distiller against a fixture set of proofs/corrections/outcomes). Do NOT push or open PRs — Ember
merges after the independent AI review.

## Done / Proof
independent-AI-reviewed branch with: (1) `feature_outcome` ledger signal live + one real row written
for a recently-merged spec, (2) `tools/academy/distill.py` producing a non-empty `core/STATE/ACADEMY.md`
with ≥1 principle traced to evidence, (3) staged nightly launchd plist for James to load. Ready for merge.
