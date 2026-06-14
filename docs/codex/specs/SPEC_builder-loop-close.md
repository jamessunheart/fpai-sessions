# SPEC_builder-loop-close

*Rung 4 of the System-That-Builds-The-System ladder. Wire the Ember-as-builder pipeline
end-to-end: a new `build:` intent in Telegram auto-flows through spec-draft → Codex build →
Ember review → TG reply → James blesses merge. James speaks; the loop builds. Owner: Codex.*

## Source / why
The builder lane (shipped 2026-06-11, `04909b95`) captures `build:` TG messages into
`core/BUILD/intents/`. But steps 2-4 of the pipeline are still manual triggers:
Ember has to notice the intent file, draft a spec, fire `run_codex.sh`, review the diff,
and post back to TG by hand. Rung 4 closes that: a watcher fires the whole chain
autonomously, stopping only at the Reserved-Class boundary (merge = James's irreducible gate).

Memory: `project-apprentice-unbottleneck-model` · buildstream intent `rung4-hubs`.

## The three declarations
- **Milestone (DoD):** `tools/queue/build_loop_watcher.py --once` reads all `status: open`
  intents in `core/BUILD/intents/`, drafts a spec for each via `tools/spec/draft.py`,
  invokes `tools/build_loop/run_codex.sh --spec <path>` in a fresh worktree, writes a
  review file to `core/BUILD/reviews/<id>-<slug>.review.md`, and sends one TG message per
  build: *"Built `<slug>` — tests green. Merge? ⚡ (reply `merge` or `reject`)"*.
  Intent status transitions: `open → spec-drafted → building → review-pending`.
  No auto-merge. No auto-deploy. Merge gate stays with James.
- **Dependency:** Rung 3 (`tools/spec/draft.py` ✅) · capture lane (`build_intent_router.py` ✅) ·
  `run_codex.sh` ✅ · TG send util (`tools/queue/verb_router.py` or `telegram_send.py`).
  Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main` without explicit review.

## Definition of Done

1. **`tools/queue/build_loop_watcher.py`** — `watch_once(intents_dir, specs_dir, reviews_dir) -> list[str]`:
   - Scans `core/BUILD/intents/` for any file with `status: open`.
   - For each: calls `tools/spec/draft.py draft_spec(intent)` → writes `core/BUILD/specs/<id>-<slug>.md`.
   - Calls `tools/build_loop/run_codex.sh --spec <spec_path>` (subprocess, captures stdout/stderr).
   - Reads the result diff from `core/BUILD/results/<id>.result.md` (written by run_codex.sh).
   - Writes `core/BUILD/reviews/<id>-<slug>.review.md`: diff summary · test pass/fail · risks · merge-or-reject recommendation.
   - Sends TG message via the existing send utility: `"Built <slug> — <test_status>. Merge? ⚡ Reply 'merge <id>' or 'reject <id>'."` 
   - Updates intent frontmatter: `status: review-pending`, `review_path: core/BUILD/reviews/...`.
   - Appends to `core/BUILD/PROOF_LOG.md`: `[UTC] · <stream> · builder loop: <slug> · REVERSE: git branch -D build/<id>`.
   - **Hard stops (Reserved-Class gates):** no `git merge`, no `git push`, no deploy, no secrets, no money, no live sends beyond the one TG review notification.

2. **`tools/queue/test_build_loop_watcher.py`** — tests with fixtures (no live Codex, no real TG sends):
   - An `open` intent → spec drafted, result file present → review written, intent status updated.
   - A `review-pending` intent → skipped (idempotent, not re-processed).
   - Codex subprocess failure → intent status set to `build-failed`, TG message says so; watcher does not crash.
   - Reserved-Class boundary respected: no merge/push calls in any code path.

3. **`tools/build_loop/run_codex.sh`** gains a `--spec <path>` flag (currently uses SPECS dir sweep):
   - When `--spec` is passed, builds only that one spec.
   - Writes result to `core/BUILD/results/<spec_id>.result.md`.
   - Dry-run (`--dry-run`) prints the codex command but executes nothing.

4. **`core/BUILD/` directory scaffold** (create if absent):
   - `core/BUILD/specs/` — builder-lane specs (distinct from `docs/codex/specs/` Codex-queue specs)
   - `core/BUILD/results/` — Codex output per build
   - `core/BUILD/reviews/` — Ember review per build

5. **Wire into `daily_sync.py`** — call `build_loop_watcher.watch_once()` after
   `build_intent_router.capture()` so the full chain fires on every daily sync tick.
   Guard with `FPAI_BUILD_LOOP_DISABLE=1` kill-switch.

## Files
- **Files ALLOWED:**
  - `tools/queue/build_loop_watcher.py` (new)
  - `tools/queue/test_build_loop_watcher.py` (new)
  - `tools/build_loop/run_codex.sh` (add `--spec` flag only)
  - `tools/decisions/daily_sync.py` (one import + one call)
  - `core/BUILD/specs/.gitkeep`, `core/BUILD/results/.gitkeep`, `core/BUILD/reviews/.gitkeep` (new dirs)
- **Files FORBIDDEN:** `core/BUILD/intents/` (read-only from watcher) · `docs/codex/specs/` ·
  any live service code · production deploy state · secrets · money movement · non-draft specs
  without explicit promotion · unrelated refactors.

## Safety
- 🔴 **Merge gate stays with James.** The watcher sends a TG notification; it never merges.
- 🔴 **No live sends beyond the review notification.** The TG message is informational only.
- 🔴 **Codex build failure is safe.** Watcher sets `status: build-failed` and notifies; does not crash or retry infinitely.
- 🔵 Kill-switch: `FPAI_BUILD_LOOP_DISABLE=1` skips the watcher call entirely.
- 🔵 Idempotent: `review-pending` and `build-failed` intents are never reprocessed without a manual reset to `open`.
- Rollback: `git revert <this-commit>` removes the watcher; existing intent files are unaffected.

## Tests
- `python3 -m pytest tools/queue/test_build_loop_watcher.py -v`
- `python3 tools/queue/build_loop_watcher.py --dry-run` — prints what it would do, writes nothing.
- `git diff --check` scoped to allowed files.

## Rollback
- `git revert <this-commit>` removes watcher + daily_sync wire.
- `rm -rf core/BUILD/specs/ core/BUILD/results/ core/BUILD/reviews/` — clears scaffold.
- Intent files in `core/BUILD/intents/` are unchanged; reset status to `open` to reprocess.

## Close-out
Update `docs/codex/HANDOFF.md` in the Codex → Ember lane:
- Files changed · tests passing · dry-run verified · intent flow demonstrated.
- Intent solved: builder loop self-runs from capture to TG review notification.
- Downstream intent unlocked: Rung 4 hubs (comms · financial · recruiting) can now be built
  by speaking `build: <hub name>` from Telegram — James speaks, the system delivers.
- Proof: one end-to-end run logged in `core/BUILD/PROOF_LOG.md`.
