# BUG LOG — the brain's fault record

The orderly record of every bug found, its **root cause** (not just symptom), how
it was fixed, the **brain version** it was fixed in, and the git ref to **revert**
to. Append-only. Newest first.

**The flow:** error (ops_ledger) → root cause (`tools/rca/autonomous_rca.py`) →
fix (git commit) → **BUG_LOG entry** → **Guard** (the rule that prevents recurrence) →
version bump + git tag → if the root is structural, it graduates to a Principle in
[AI_PRINCIPLES.md](AI_PRINCIPLES.md).

**P8 — every bug becomes a rule.** A bug is not FIXED until a durable **Guard**
exists: a regression **test**, a **Principle**, or an automated **check** (RCA
signature / Constitution Check / circuit breaker). `tools/academy/bug_rule_audit.py`
fails CI if any FIXED bug has no guard — the discipline is enforced, not hoped.

**Revert:** `git checkout brain-v<X.Y.Z>` returns the brain to any tagged version.
Versioning: MAJOR = architecture change · MINOR = new capability · PATCH = bug fix.

**Status vocab:** FIXED (root fixed + verified + **guarded**) · MITIGATED (symptom
handled, guard pending) · ROOT-CAUSED (root known, class-fix + guard queued) · OPEN.

---

## Brain v1.0.0 — 2026-07-03 · structured versioning begins
_Anchor. Prior state = ~6 months, 125 merged specs, no version tags. This is the first tagged brain version and the first structured bug batch._

| ID | Symptom | Root cause | Root (P#) | Fix | **Guard (the rule)** | Status |
|----|---------|-----------|-----------|-----|----------------------|--------|
| BUG-001 | Awareness probe scored 0% for 79 probes | Probe imported the **repo** build_context, not the live bot; repo copy's DB import fails silently | [P2](AI_PRINCIPLES.md) | Probe targets live path, repo fallback | check: probe live-path + 100% probe metric watched by `fpai-awareness-reliability.timer` | FIXED |
| BUG-002 | 207/212 corrections garbage (empty original) | Fired on bare words with no verified prior bot turn — signal without referent | [P1](AI_PRINCIPLES.md) | Require phrase + real bot turn; purged 207 | **test:** `test_detect_correction.py` (5) | FIXED |
| BUG-003 | Reality-check marked all 113 merged specs "dead" + queued 113 repairs | Demanded proof from an unwired channel; overwrote `build_status` with a liveness verdict | [P2](AI_PRINCIPLES.md) [P6](AI_PRINCIPLES.md) | `reality_status` only + circuit breaker | **test+check:** `test_post_merge_reality_check.py` (dead-rate breaker) + P6 | FIXED |
| BUG-004 | Nightly metabolism ran but shipped nothing | Wrote a prompt then stopped — merged-but-dead | [P1](AI_PRINCIPLES.md) | Bridge work-order → decision → build loop | **test:** `test_nightly.py` (queue_build_decision) | FIXED |
| BUG-005 | d143/d144 unbuilt ~12h ("strategic wait") | `spec_written=true` set before build; failed build orphans the decision | [P1](AI_PRINCIPLES.md) | Data unblock (reset flag) | ⏳ PENDING — durable query fix (`pending_builds` include build_status='none') not shipped | MITIGATED |
| BUG-006 | `diagnostic_error` 96× (swallowed) | `curator` name collision — repo stub + live pkg share the namespace | [P2](AI_PRINCIPLES.md) [P3](AI_PRINCIPLES.md) | RCA identified | ⏳ PENDING class-fix (rename + fail-loud import guard); RCA signature catches recurrence | ROOT-CAUSED |
| BUG-007 | 26 worktrees stuck >24h | Work-items created assuming terminal state; no reaper | [P1](AI_PRINCIPLES.md) | RCA identified | ⏳ PENDING class-fix (terminal-state reaper); RCA signature catches recurrence | ROOT-CAUSED |
| BUG-008 | `debate_error: no JSON object` 13× | LLM text treated as guaranteed-parseable; no tolerant extractor | [P2](AI_PRINCIPLES.md) | RCA identified | ⏳ PENDING class-fix (shared `robust_json()`); RCA signature catches recurrence | ROOT-CAUSED |
| BUG-009 | Constitution Check read only proposal **title**, ignoring `build_spec` — gated on title alone | `_proposal_text` field list omitted the fields callers pass (`build_spec`/`why`) | [P2](AI_PRINCIPLES.md) | Added the caller fields to the scan | **test:** `test_reads_build_spec_not_just_title` | FIXED |
| BUG-010 | Doctrine claimed the checker "scores all 8 laws"; it screened ~3 | Overclaim — claim outran the wiring (claimed≠wired, applied to my own work) | [P4](AI_PRINCIPLES.md) [P2](AI_PRINCIPLES.md) | 6/8 laws screened + `--law-map` + claim corrected | **tests:** `test_supreme_law_tradeoff_blocks`, `test_irreversible_needs_positive_reversibility` + `--law-map` | FIXED |

**Class-fixes still owing a guard (BUG-005/006/007/008 → the next builds):** durable
`pending_builds` query · eliminate `curator` name collision + fail-loud import guard ·
terminal-state reaper for every pipeline work-item · one shared `robust_json()` at
every LLM→JSON boundary. Each closes its bug AND becomes a standing rule.

---

## Autonomous findings (appended by `tools/rca/autonomous_rca.py`)
_Root causes the RCA reflex confirmed on its own, newest first. One row per root (not per symptom). These graduate to [AI_PRINCIPLES.md](AI_PRINCIPLES.md) when structural._

| Detected | Seen | Loop | Root cause | Class-fix | Sev/Conf |
|----------|------|------|-----------|-----------|----------|
<!-- RCA-APPEND-BELOW -->
| 2026-07-03 | 1x | council | Violated invariant: output format must be a function of the CONSUMER (human vs. code), but the system binds a single human-oriented output-style contract global | Introduce an explicit audience boundary for model calls: (1) a machine/structured invocation profile that suppresses the caveman output styl | high/high <!-- sig:a885efa0fe --> |
| 2026-07-03 | 1x | council | Violated invariant: the system treats free-form LLM CLI output as if it were guaranteed-structured data. Parsing happens at the boundary with no schema enforcem | Introduce one shared LLM-output boundary contract used by ALL CLI-model consumers: (1) request structured output via schema/tool-call or str | med/med <!-- sig:69c15d931d --> |
| 2026-07-03 | 1x | build | The build loop assumes builds are atomic against a frozen base (build-time tree == merge-time tree), but the repo is concurrently mutated by parallel sessions a | Make integration base-aware instead of atomic-assumed: at build-start capture base SHA into the spec; at merge-time, if HEAD != base, auto-r | med/med <!-- sig:b53f49e962 --> |
| 2026-07-03 | 3x |  | Violated invariant: 'hook/timer-invoked scripts run with the same environment as interactive shells.' They don't — and placeholder-credential fallbacks ('change | One canonical environment shim (e.g. /etc/sh-brain/brain.env validated + a tools/lib/brain_env.sh that resolves venv python + BRAIN_INDEX_DB | med/high <!-- sig:1253f0ea21 --> |
| 2026-07-03 | 11x | build | End-of-pipeline constraints are invisible at the start of the pipeline: the protected-path (watchdog-layer) rule exists only in the reviewer, so the proposer ke | Shift constraints left and close the loop: (1) publish the protected-path registry (and other merge-gate rules) as a machine-readable file c | med/high <!-- sig:27dda2cbe6 --> |
| 2026-07-03 | 13x | council | Violated invariant: 'CLI output is determined solely by the prompt I pass.' Reality: output = prompt + ambient session config (output style, CLAUDE.md persona,  | Create one shared `machine_claude()` wrapper (single module all loops import — debate.py, ai_review, RCA, scanner) that invokes claude -p wi | high/high <!-- sig:101965c06c --> |
| 2026-07-03 | 26x | health | The build-worktree lifecycle has no owned garbage-collection / terminal-disposition path. Every created worktree is assumed to reach one of two happy endings (a | Give every build worktree a guaranteed terminal disposition instead of an open-ended 'wait for James'. Add a reaper in the health/build loop | med/med <!-- sig:e23fa2e502 --> |
| 2026-07-03 | 96x | council | Top-level import-name collision: two distinct `curator` packages (repo-local cockpit helpers vs deployed brain service) occupy the same import namespace. The in | Eliminate the namespace collision — rename the repo-local package (e.g. `curator/` → `cockpit_curator/` or nest it under an existing repo na | high/high <!-- sig:14a098ff33 --> |


## 2026-07-03 — Zombie API burn (2nd occurrence of class)
**Symptom:** James received $15.27 Anthropic auto-recharge invoice (#97 on the account!). **Root cause:** brain-curator systemd TIMER fleet (Apr era) called metered Sonnet daily; its input feed (tg-capture) died May 7 → 2 months of paid calls producing `final_brief_count: 0`. Prior same-class: metaclaw (Apr 30). Neither caught by system — caught by invoice. **Deeper cause:** spend had no registry, no output-check; timers hide from service-level scans. **Fix:** 5 timers disabled · key revoked (James) · **Law: NO UNMETERED BURN** + tools/burn/audit.py weekly enforcer (fleet key-scan + journal attribution + burn-vs-output). **Hunt pattern that worked:** journalctl -o json → _SYSTEMD_UNIT attribution.

## 2026-07-03 — "Ads take days" + "send to a warm person" (two-part miss, James-caught)
**Symptom:** (a) told James to manually share /assessment with a warm person to get the first audit; (b) estimated autonomous ads as "days." **Root cause:** (a) routed reversible AI-doable distribution to James despite owning the ad account — Sunheart Rule inversion; (b) conflated the autonomous generate→breed LOOP (a real build) with creating the FIRST ad (direct Graph API, minutes) — and never probed to the real gate. **The real gate (found by probing Graph API directly):** system user `adportalsystemuser` lacks ad-CREATE role on act_71883338 (code 200 / subcode 1815066) + no Facebook Page connected. Two ~5-min Meta Business-Settings grants — not a build, not days. **Fix:** Law PROBE-TO-REAL-GATE / MINIMAL-FIRST-INSTANCE added to AI_PRINCIPLES.

## 2026-07-03 — "fpull but don't see it in vault" (the doubled-path root cause, weeks-old)
**Symptom:** repeatedly, mirrored doctrine/academy never appeared in James's Obsidian vault after fpull. Recurred across sessions. **Root cause (found by isolating the write):** `mirror_pull.py` main() set `vault = digest_file.parents[1]` — but digest_file = `vault/02_CONTEXT/Memory/BRAIN DIGEST.md`, so parents[1] = `vault/02_CONTEXT`, not the vault root. `mirror_state_docs` then wrote to `vault/02_CONTEXT/` + `02_CONTEXT/Academy/...` = a phantom **`02_CONTEXT/02_CONTEXT/Academy/`** folder James never opened. One off-by-one index hid ALL mirrored content for weeks. **Fix:** `parents[1]` → `parents[2]` (vault root). Also: fpull never git-fetched from 162 (added fetch+ff-only step) and the laptop branch had diverged from 162's feat/headless-build (reconciled, one head). **Lesson:** when a mirror "reports success" but the file isn't where expected, the write TARGET is wrong, not the write — isolate and print the resolved dest path.

## 2026-07-04 — Greenlit build slept in the vault ("why no progress while I sleep?", James-caught)
**Symptom:** James greenlit the 7-Areas life-assessment instrument ("sounds good") in the evening; next morning nothing was built. **Root cause:** the spec existed only as a vault strategy doc (`04_DECISION/Offers/…Sprint MVP Spec`) — never written into `core/BUILD/specs/`, the only place the 162 loop reads. I then compounded it by ending replies "on your word" — re-asking for a permission already granted (act-don't-ask violation). Decided ≠ queued: the system's intent lived in a human-readable surface the executor never scans. **Fix:** engine built + proven same turn (`tools/growth/life_assessment/score_life.py --demo`), spec queued (`SPEC_life-assessment-7areas.md`), **Law P12 DECIDED ≠ QUEUED** added to AI_PRINCIPLES. **Lesson:** every greenlight must land in the executor's queue the same turn — strategy docs don't build.

## 2026-07-04 — Sibling's uncommitted work destroyed by "residue" checkout (self-caught during cross-reference)
**Symptom:** 162's parallel session committed "re-add Law of Intelligent Allocation — LOST to a parallel-session collision" (0b553ba4). **Root cause:** during a push-window clear I ran `git checkout -- core/STATE/ALLOCATION_INTELLIGENCE.md` on 162's live checkout, assuming the dirty file was my own stash residue. It was the sibling session's in-progress uncommitted edit. Assumption "only I edited this file today" was false in a multi-session system. **Fix:** Law P13 (diff-before-discard on shared checkouts) + operational default: unknown dirty tracked files get COMMITTED as checkpoints, never discarded. **Lesson:** on shared checkouts, dirty = presumed sibling work until diffed.

## 2026-07-04 — Named specs invisible to the build loop (3-week silent rot)
**Symptom:** SPEC_cartographer-auto-refresh / lantern-detector / mirror-digest / proof-river sat in core/BUILD/specs/ since Jun 14, never built; SPEC_life-assessment-7areas would have joined them. **Root cause:** the loop is decision-driven (brain_index.decisions WHERE needs_build); the orphan-seeder (seed_orphaned_specs.py) only matches `SPEC_dNNN` filenames — named specs match nothing, so the file-queue and the real queue silently diverged. Same class as d134's orphaning bug (spec exists, executor blind). **Fix:** renamed live spec → SPEC_d149 + seeded (verified row: needs_build=true); Law P14 (verify queue visibility at the executor's actual selector); class-fix queued as SPEC_d150. **Lesson:** presence in a directory ≠ presence in the queue — verify at the selector.
