# SPEC d169 — Vault reorg tier-2: one answer per question, machine files out of James's path

**Source:** 3-lens Sonnet audit 2026-07-04 (structure · James-UX · script-dependency). Tier-1 already done by hand (307MB album_export → cold storage · stale forks → 99_ARCHIVE · START HERE = 10-line door · SYSTEM MAP split out; vault git 8f8c70f). This spec is the code-touching remainder. Vault: `~/Documents/FPOS/Full Potential OS/`. ⚠️ Consult the dependency map FIRST: ~20 scripts write hardcoded paths into `02_CONTEXT/Memory/`; installed `~/Library/LaunchAgents/com.fpai.vault-sync.plist` `FPAI_VAULT_NOTE_DIRS` is the authoritative scan list (repo plist copy is stale).

## Build (in order, each reversible via vault git)
1. **Weld the split PROOF LOG (the landmine).** Two files, different writers: `06_RESULTS/PROOF LOG.md` (proof/pull_162.py, scout_run.py) vs `02_CONTEXT/Memory/PROOF LOG.md` (push_update, daily_sync, proof/log.py, index+selfmodel refresh). Pick `06_RESULTS/` as canonical (lifecycle-correct); repoint the Memory writers (proof/log.py:30-39 etc.); leave a pointer note at the old path.
2. **Collapse the state fork — ONE "now" page.** `CURRENT STATE.md` = the only James-facing state file. `NOW MIRROR`, `NOW — Current Priorities`, `HOT STATE`, `BRAIN STATE`, `SYSTEM READINESS`, `SYSTEM SELF-MODEL` move to `02_CONTEXT/Memory/_machine/` (new subfolder) — update each writer's dest path (now_mirror.py:38, mirror_pull.py L243-258 dest map, reflect/log.py, selfmodel/refresh.py). They remain machine inputs; never linked from HOME/START HERE.
3. **Sort the 70-file flat Memory pile** into existing subfolders by function: `_maps/` (the 6 INDEX/MAP files — keep INDEX OF INDEXES as machine artifact there), `_ledgers/` (BURN AUDIT, COST LEDGER, HEARTBEATS, FRESHNESS CHECK), `_machine/` (step 2 files + SCENES, SURFACED CONCEPTS, HUB CHARTS…), keeping ≤12 James-facing files at Memory root (TREASURY TODAY, TREASURY CHART, DECISIONS, BUILDSTREAM BOARD, CURRENT STATE, PROOF pointer…). Update every writer's dest (§1 dependency table in the audit) + `FPAI_VAULT_NOTE_DIRS` if paths change + `launchctl unload/load com.fpai.vault-sync`.
4. **GOALS trio → one.** `AI GOALS.md` (auto-mirror) stays canonical; `GOALS MIRROR` → `_machine/`; `My Goals.md` merge-or-archive (council judges).
5. **HOME template:** add `🔨 Built recently → [[BUILDSTREAM BOARD]]` to daily_sync.py's HOME writer (currently missing from HOME's go-deeper list).
6. **MINDMAPS INDEX auto-regen:** generate from folder listing (95 maps today; hand-count claimed 82; 5 maps unindexed: 53-56, 91). No hardcoded counts in prose anywhere.
7. **Post-move guard:** run one full vault-sync + daily_sync + heartbeat cycle; verify every regenerated file lands at its NEW path (P14: the destination is the queue — verify at the selector). Vault git commit per step.

## Contract
$0 · every step reversible (vault git + repo git) · one step per commit · independent review · verify feeds green after each move (HEARTBEATS shows 13/13). NEVER move `02_CONTEXT/Academy/` or `_ember_memory/` by hand (fully regenerated).

## Done / Proof
James's phone view: Memory root ≤12 files · one CURRENT STATE · one PROOF LOG · HOME links Built-recently · MINDMAPS INDEX count matches disk · all heartbeats green after 24h.
