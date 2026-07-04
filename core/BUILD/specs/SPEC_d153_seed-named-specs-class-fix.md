# SPEC d153 — Class-fix: named specs must be visible to the build loop (or rejected loudly)

**Root cause (BUG_LOG 2026-07-04, Law P14):** the loop selects from `brain_index.decisions`; `tools/build_loop/seed_orphaned_specs.py` only recognizes `SPEC_dNNN*` filenames. Named specs (`SPEC_foo.md`) rot silently — 4 sat unbuilt since Jun 14.

## Build (pick A, fall back B)
**A (preferred):** extend `seed_orphaned_specs.py` to also seed named specs: for any `core/BUILD/specs/SPEC_*.md` without a decision row, allocate the next free dNNN id FROM THE DECISIONS DB (MAX(id)+1 — files do NOT own the namespace; file-side numbering caused the d150/d151 collisions this spec now also fixes), rename the file to `SPEC_dNNN_<slug>.md` (git mv, committed), and seed the row (needs_build=true, same as today). Idempotent; dry-run flag preserved.
**B (if renaming is judged unsafe):** a loud gate — the seeder (or a health check) alerts to TG/HOT_STATE whenever a named spec exists >24h without a decision row, naming the file. Silence is the bug.

Also: seed-or-flag the 4 existing June-14 named specs (cartographer-auto-refresh · lantern-detector · mirror-digest · proof-river) — seed if still wanted, archive with a note if stale (council judges).

## Contract
$0 · reversible (git mv + DB rows) · independent review before merge · runs under the same env/creds as the awareness probe (BRAIN_INDEX_DB_URL via the working systemd env pattern).

## Done / Proof
A fresh named `SPEC_test-canary.md` dropped in specs/ gets a decision row (or a loud alert) within one seeder cycle, evidence in the commit + a BUG_LOG follow-up line.
