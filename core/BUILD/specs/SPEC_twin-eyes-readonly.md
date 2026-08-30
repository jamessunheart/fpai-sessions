# SPEC_twin-eyes-readonly

## Approval

James approved proceeding on 2026-08-29 after an external architecture review approved only the read-only Twin Eyes Card and held semantic detection plus autonomy gating for evidence.

## Intent

Create the first visible Current Reality Card: a deterministic, read-only lens that shows sourced claims across freshness, agreement, and evidence without becoming an authority or changing system state.

## Adjacent Intent Unlocked

A hand-labelled contradiction corpus can test whether a future detector is trustworthy before any conflict signal is allowed to affect autonomous work.

## Branch

`codex/twin-eyes-readonly`

## Files Allowed

- `tools/twin_eyes/**`
- `core/BUILD/specs/SPEC_twin-eyes-readonly.md`
- `core/BUILD/REGISTRY.json`
- Codex-owned run entry in `docs/codex/HANDOFF.md`

## Files Forbidden

- Source state files under `core/STATE/**`
- Vault files
- Services, hooks, daemons, timers, deployment files, and production configuration
- Money, outreach, secrets, model calls, network calls, and autonomous actuation

## Build

1. Read an explicit JSON manifest of topics and observations.
2. Verify observation evidence only by literal text in allowlisted repo-relative files.
3. Compare hand-normalized values within each topic:
   - two or more verified values: `conflict`
   - exactly one verified value and no unverified competing observations: `clear`
   - otherwise: `unknown`
4. Report each topic across orthogonal dimensions:
   - `freshness`: `fresh | stale`
   - `agreement`: `clear | conflict | unknown`
   - `evidence`: `verified | claimed | none`
5. Require an explicit `--as-of` time so JSON and HTML outputs are byte-reproducible.
6. Render a local baseball-card-style HTML view. It may flip and filter locally, but must contain no chat, write, gate, send, deploy, or action control.

## Definition Of Done

- Default demo corpus reproduces the known `Discovery` vs `Value Capture` and `48` vs `69` contradictions.
- Known-conflict recall is 100%, with zero false `clear` results on the known-broken corpus.
- Every observation includes source path, source timestamp, exact evidence text, and a source digest.
- Repeated runs with identical inputs and `--as-of` produce byte-identical JSON and HTML.
- Paths outside the repository are rejected.
- The card labels itself `LENS ONLY · NO AUTHORITY · NO ACTUATION`.
- No source file is modified.

## Tests

- `python3 -B -m unittest tools.twin_eyes.test_card`
- `python3 -m py_compile tools/twin_eyes/card.py tools/twin_eyes/test_card.py`
- Demo generation twice followed by byte comparison
- `python3 -m json.tool tools/twin_eyes/demo_manifest.json`
- `git diff --check`

## Risks

- Normalized values are curated labels, not semantic understanding.
- Freshness thresholds are experiment policy, not doctrine.
- A derived view can drift; it must never be cited as a source of authority.

## Rollback

Delete `tools/twin_eyes/`, this spec, and its registry/handoff entries. There is no runtime process or production state to unwind.
