# SPEC_d130 — Witness→Question engine (the Curiosity Engine, elevated)

Authored by Ember, 2026-06-30, after James named the real center: *"the system needs to get better at
witnessing and asking questions that lead to better improvements — that's the whole point."* This is
the steering wheel ABOVE the engine (Observe→Question, the top of the scientific core loop). Reprioritized
from last to FIRST in the build queue, because a better question changes which part of reality the whole
flywheel explores. We have built answer-machines; we have not built the thing that asks.

**The gap, named honestly:** Every improvement in the 2026-06-30 session came from James's question, not
the system's answer. The system has no organ that witnesses its own state and generates the question that
breaks a weak assumption. This is the pinned [[reference-introspective-self-chat-gap]] and the open qb
question "self-chat is extrospective (what to build for James) not introspective."

## Build

A loop, reusing organs we already have. NOT a new agent — a wiring of witness → question → reality.

1. **Witness** (reuse `true-narrator` + ground truth): each cycle, read what ACTUALLY happened — recent
   transcripts, file diffs, decision outcomes, the d132 conversion ledger, feature_outcome rows, where
   reality disagreed with expectation. Forensic, not flattering.
2. **Question generator** `tools/curiosity/ask.py`: from the witnessed state, generate INTROSPECTIVE
   questions — "what assumption am I holding that the evidence contradicts? where is a conversion weakest
   and why? what did reality disagree with this week? what am I uncertain about that matters?" Default to
   the question that exposes the weakest assumption, not the most. Opens them into qb (introspective book).
3. **Route to improvement**: a generated question that the system can act on becomes a build-decision (via
   the existing `decisions.queue_build` path) or surfaces to James one-at-a-time (the proven one-chat).
4. **Close the loop (the honesty tie)**: a question is only "good" if it LED to a real improvement. Tag each
   question with the outcome of what it triggered (feature_outcome=improved / flat / regressed). Questions
   that produced improvements get reinforced; questions that produced nothing get pruned. This is what makes
   curiosity compound instead of drift into clever-but-useless. The Academy (d129) distills "question
   shapes that led to improvement" into a reusable questioning curriculum.

## Context — why FIRST, not last

The three flywheel diagrams converge: questions are search operators; if questions improve, the probability
of discovering leverage improves. This sits above compute, context, build, deploy. We reprioritized the
whole queue around it. Measurement (d132) and the outcome signal (d129) are PREREQUISITES — they give the
witness real ground truth and let the loop know which questions actually worked. So order is:
**d129 (outcome signal) → d132 (conversion ledger = the witness's eyes) → d130 (this) → d131 (metabolism acts on the questions) → d133 (public interface gives the witness real-user data).**

## Honest constraints (load-bearing)
- 🔴 Questions route through the EXISTING safety layer (review · veto · protected-paths). The curiosity engine
  proposes; it never auto-executes outside Trust-tier bounds. James can veto any question-driven build.
- 🟡 Anti-confabulation (the 2026-06-14 fix): the witness reports ground truth only — no encouraging fiction.
  A question must cite the real evidence that provoked it.
- 🟡 Guard against question-spam: default to proposing AT MOST one high-leverage question per cycle (the
  conservative recommend.py discipline), not a flood.

## Contract
Follow `docs/codex/SESSION_CONTRACT.md`. Branch off `feat/headless-build` (never main).
Register in `core/BUILD/REGISTRY.json` (status building->done). Tests required (fixture-test that a witnessed
state with a known weak assumption produces a question citing the real evidence; assert it does NOT fabricate).
Do NOT push or open PRs — Ember merges after independent AI review.

## Done / Proof
independent-AI-reviewed branch with: `tools/curiosity/ask.py` that witnesses real state (transcripts/diffs/
ledger), generates ≥1 introspective question citing evidence, opens it to qb, and tags it with the outcome of
what it triggered. One real cycle run end-to-end producing a question that surfaces a genuine weak assumption.
Ready for merge.
