# SPEC_consequence-learn-loop

*For Conscious Codex 3 (apprentice/reflection domain — owns `tools/apprentice/reflect.py`). Close the turns→learns gap: record whether a shipped move actually realized the unlock it claimed (result landed? next run cheaper/lighter?), and feed that back as weighting/insight. Make the loop learn from consequences, not just completions. Owner: Codex. Read+record+propose; no auto-action.*

## Source / why
Doctrine (memory `feedback-turns-vs-learns-and-safety-gate`): Cycle Zero proved the loop *turns*, not that it *learns*. Every proof row claims "unlocks next: X" but nothing checks if X realized. The apprentice `reflect.py` already summarizes recurring pauses — extend it into a consequence tracker so the system learns.

## The three declarations
- **Milestone (DoD):** `tools/consequence/watch.py` (or extend `apprentice/reflect.py`) reads PROOF LOG / ledger entries, and for each shipped move records a consequence verdict — `realized` / `not-yet` / `no` — against its claimed unlock, with evidence. Produces a `docs/codex/CONSEQUENCE_REPORT.md` summarizing what actually landed vs what was claimed, and a one-line "next improvement" suggestion.
- **Dependency:** `tools/apprentice/` + PROOF LOG. Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main`.

## Definition of Done
1. Parse recent proof/ledger rows (intent solved · unlock claimed). For each, check observable evidence the unlock realized (file exists · gate answered · test passes · result recorded) → verdict + confidence.
2. Aggregate: realized-rate, recurring non-realizations (e.g. "approve & send" keeps not landing because James hasn't answered), and one suggested next move.
3. Optional: feed `realized` results as a small weight bump to the originating results-opportunity (proposal only, written to a review lane — NOT auto-applied to the buildstream).
4. Tests: a realized-unlock fixture → `realized`; a claimed-but-absent unlock → `not-yet`/`no`; report aggregates correctly; dry-run writes nothing.

- Files ALLOWED: `tools/consequence/**` (new) or `tools/apprentice/reflect.py` · `docs/codex/CONSEQUENCE_REPORT.md` · read-only of PROOF LOG/ledger/buildstream. FORBIDDEN: auto-editing the buildstream/weights · money/send/deploy/secrets · live autoloop wiring.

## Safety
- 🔴 Records + proposes only; never auto-changes weights or ships anything. Uncertain → `not-yet`, flag for review.
- Rollback: delete the new module + report.

## Close-out
HANDOFF 📥 · PROOF LOG (the loop now learns from consequences, not just completions — turns→learns) · BRICK (the consequence-watch pattern).
