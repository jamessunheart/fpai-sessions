# SPEC_d153_spec-d153-class-fix-named-specs Result

## Status
Done in working tree / awaiting independent review + merge.

## Summary
Extended `tools/build_loop/seed_orphaned_specs.py` so the decision-driven build loop can see named `core/BUILD/specs/SPEC_*.md` files. Existing numbered specs still seed their filename ID. Named specs now get the next available dNNN ID from `brain_index.decisions` (`MAX(id)+1`), avoid local numbered-file collisions, insert an answered `needs_build=true` decision row, and then rename the file to `SPEC_dNNN_<slug>.md` with `git mv` when running inside the repo.

Dry-run mode preserves the old safety behavior: it reports the IDs that would be seeded without writing DB rows or renaming files.

## Tests
- `python3 -B -m unittest tools.build_loop.test_seed_orphaned_specs` (8 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/seed_orphaned_specs.py tools/build_loop/test_seed_orphaned_specs.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d153-registry.json`

## Risks
Live DB mutation and live repo renames were not run in this sandbox. The first production seeder cycle may rename multiple existing named specs if they still lack decision rows. That is intended by the spec, but review should verify the queued set before merge if any named specs are stale rather than still wanted.

## Rollback
Code rollback is reverting this branch. Runtime rollback for any seeded named spec is reversible: delete the seeded `brain_index.decisions` row if it has not been built, then `git mv SPEC_dNNN_<slug>.md SPEC_<slug>.md` in the repo.

## Intent solved
Named spec files can no longer rot silently outside the executor's actual `brain_index.decisions` selector.

## Downstream intent unlocked
The build loop can safely accept human-readable named spec drops because one seeder cycle converts them into visible dNNN decision rows or fails loudly under `--strict`.
