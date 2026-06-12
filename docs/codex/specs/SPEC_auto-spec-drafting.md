# SPEC_auto-spec-drafting

*Rung 3 of the System-That-Builds-The-System ladder. The system drafts its OWN next spec: given a buildstream intent that has no spec yet, generate a well-formed `SPEC_*.md` draft (house format + the three declarations) into `docs/codex/specs/`, marked DRAFT for review. This is the "system builds system" rung — it removes James/Ember from writing every spec. Owner: Codex. Drafts only — a drafted spec is a proposal, never auto-dispatched or auto-built.*

## Source / why
James, 2026-06-09: build the system that builds the system. Rung 2 (the foreman) runs apprentices across the buildstream, but every intent still needs a human-written spec before it can build. Rung 3 closes that loop: the system proposes its own specs, so the buildstream can extend itself. Memory: `project-apprentice-unbottleneck-model`.

## The three declarations
- **Milestone (DoD):** `tools/spec/draft.py` takes a buildstream intent lacking a spec and writes `docs/codex/specs/SPEC_<slug>.draft.md` containing: intent/why · the three declarations (milestone · dependency · landing-target) · a Definition of Done skeleton · files-allowed/forbidden placeholders · safety + rollback · close-out. Marked clearly as DRAFT — needs Ember/James review before it becomes dispatchable.
- **Dependency:** Rung 2 (`tools/loop/`) + the spec house format (`docs/codex/specs/SPEC TEMPLATE` / existing specs). Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main`.

## Definition of Done
1. **`tools/spec/draft.py`** — `draft_spec(intent) -> path`:
   - Reads the intent (id · title · next move · stream · weight · any notes).
   - Emits a `SPEC_<slug>.draft.md` in the canonical house shape (mirror an existing spec like `SPEC_apprentice-execution-tier.md`), pre-filling intent/why, the **three declarations**, a DoD skeleton, and safety/rollback. Unknown fields → explicit `TODO(review):` markers, never invented certainty.
   - **Never overwrites** an existing non-draft spec; `.draft.md` suffix + a "DRAFT — review before dispatch" banner.
2. **Review gate is mandatory:** a drafted spec is a proposal. It does NOT auto-dispatch, auto-build, or get a kickoff until a human (Ember/James) promotes it (rename `.draft.md` → `.md` after review). State this in the banner.
3. **Optional loop hook (NOT wired live):** `tools/loop/direct.py` may, in dry-run, *suggest* "intent X has no spec → draft one?" — but drafting stays an explicit call, not auto-fired, in this spec.
4. **Tests** (`tools/spec/test_draft.py`): an intent with no spec → a well-formed `.draft.md` with all three declarations present; an intent that already has a spec → no overwrite; the draft contains `TODO(review):` where info is missing; dry-run writes nothing.

- Files ALLOWED: `tools/spec/**` (new) · write `docs/codex/specs/*.draft.md` only · read-only of existing specs + buildstream. Files FORBIDDEN: overwriting non-draft specs · auto-dispatch/kickoff · any build/send/money/deploy · secrets · wiring into the live autoloop.
- Tests: as above + `git diff --check` (scoped).

## Safety
- 🔴 Drafts are proposals only. No drafted spec builds or dispatches without explicit human promotion. Missing info → `TODO(review):`, never fabricated DoD/safety. Uncertain → leave the TODO + flag for review.
- Rollback: delete `tools/spec/` + any `*.draft.md` it wrote.

## Close-out
HANDOFF 📥 · PROOF LOG (Rung 3 — the system drafts its own specs; the buildstream can extend itself, review-gated) · BRICK (the auto-spec-draft pattern). Then Rung 4 (hubs, built by the apprentice fleet) unblocks.
