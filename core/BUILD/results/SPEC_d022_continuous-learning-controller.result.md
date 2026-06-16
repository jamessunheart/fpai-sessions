# SPEC_d022_continuous-learning-controller Result

- Status: done / awaiting review + merge
- Branch: `build/SPEC_d022_continuous-learning-controller`
- Files changed:
  - `tools/learn/seed_preference_pairs.py`
  - `tools/learn/test_seed_preference_pairs.py`
  - `scripts/seed_preference_pairs.sh`
  - `core/BUILD/cron/SPEC_d022_preference_seed.cron`
  - `core/BUILD/REGISTRY.json`
  - `core/BUILD/specs/SPEC_d022_continuous-learning-controller.md`
  - `docs/codex/HANDOFF.md`
- Summary: Added the d022 preference seed exporter. It requires the d021 `preference_pair_exported` column, exports unexported `brain_index.corrections` rows to `/opt/fpai-build/data/preference_pairs.jsonl`, marks exported source rows, appends row-count proof to the ops ledger, and checks the proof condition that the JSONL has lines and no unexported rows older than 24h remain.
- Tests:
  - `python3 -B -m unittest tools.learn.test_seed_preference_pairs tools.learn.test_capture_corrections tools.learn.test_learn`
  - `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/learn/seed_preference_pairs.py tools/learn/test_seed_preference_pairs.py`
  - `bash -n scripts/seed_preference_pairs.sh`
  - `git diff --check -- tools/learn/seed_preference_pairs.py tools/learn/test_seed_preference_pairs.py scripts/seed_preference_pairs.sh core/BUILD/cron/SPEC_d022_preference_seed.cron core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d022_continuous-learning-controller.md`
- Risks: Live server 162 DB/cron proof was not run in this sandbox. The cron file is a reviewed artifact, not an installed crontab. If d021 has not added `preference_pair_exported`, the script fails closed and exports nothing.
- Rollback: Revert the changed files. Remove any installed `/opt/fpai-build/scripts/seed_preference_pairs.sh` and remove the cron line `0 2 * * * /opt/fpai-build/scripts/seed_preference_pairs.sh` if Ember installs it later.
