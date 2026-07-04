---
name: ""
metadata: 
  node_type: memory
  date: 2026-07-04
  slug: coherence-guards-doctrine-pack-protocols-swarms
  type: episodic
  originSessionId: 3c6057c8-dc93-46ef-bdd9-ba031f72bb92
---

# Session — Coherence guards → compressed doctrine → protocols & swarms

## The arc (what was alive, what shifted)

A long build session that started at "does loop timing make sense / how do they compress"
and climbed into the deepest theme of the week: **the system must operate beyond its base
training, and that only holds if it's ENFORCED, not just documented.** Every thread this
session was a variation on *map ≠ territory* and *say ≠ do*.

The pivotal moment: James caught me routing d138 to him ("which features do you want shipped?")
**one turn after re-reading the substrate-default rule.** He named the real problem — "there's a
bias in your training to default to me when it should default to the Constitution/AI-principles.
How do we ensure this EVERY session?" The honest answer: passive rules don't beat training bias.
Only a gate does. That became **P9** and a live Stop hook. This reframed the whole session: for
any training-biased behavior, build the gate — don't trust the loaded instruction.

Then James pushed the Academy idea further: compress everything we've learned, save the named
protocols so sessions know they exist, and let sessions **invent their own** protocols. The
session ended mid-flight on a team-of-Sonnets distillation (run 1 degraded by an API-529 burst;
root-caused → batched → re-running).

## What shipped (code · docs · memory)

- **Metric Coherence Guard** — `tools/governance/metric_coherence.py` (map≠territory: prose vs
  measured SSOT). History/forecast/section-aware. Wired into daily self-audit. Fixed the live
  awareness-drift (41.3%/88% vs SSOT 100%) at its ROOT (live-memory copy, not just repo).
- **identity_scanner section-aware** — HOT_STATE no longer broadcasts archived snapshots as
  active directives.
- **D138 repo≠running** — mapped the bidirectional tgbot fork (16 built-not-live fns, 12
  live-not-committed), captured live snapshot + diff + `D138_tgbot_repo_vs_live.md`. NOT
  blind-merged (prod blast radius). SSOT_REGISTRY updated with both new truth-sources.
- **P9 + Substrate-Default Gate** — `.claude/hooks/check-substrate-default.sh` (Stop hook):
  routing to James without a named Reserved class → corrective round-trip. AI_PRINCIPLES P9.
- **CORE_DOCTRINE.md** — `tools/academy/compile_doctrine.py` auto-compiles the compressed
  operating education (keystone + 8 Laws + 9 Principles + 3 wait-categories). Loaded FIRST by
  CLAUDE.md (Layer -2); injected into the council `claude -p` prompt; recompiled daily.
- **Two workflows** — `academy-distill` (corpus → compressed Academy + prune manifest) and
  `self-improvement-swarm` (probe → adversarial-diagnose → weighted intent stream → build queue).
- **PROTOCOLS registry** — `core/STATE/ACADEMY/PROTOCOLS.md` catalogs every named way-of-working
  + a 7-step "invent + name your own protocol" guide. Wired into CORE_DOCTRINE for discovery.
- **Memory:** `reference_metric_coherence_guard`, `reference_protocols_registry`, updated
  `feedback_default_to_substrate_not_james` (the enforcement layer) + MEMORY.md index lines.

## What's open (threads in flight)

- **academy-distill re-run** (task `wg14nigwb`) — batched (waves of 3) after run 1 was degraded
  by API-529 (10/11 miners died → clusters:1, lessons:10, only marketing PDFs). ON COMPLETION:
  write `CURRICULUM.md` + `PRUNE_MANIFEST.md` into `core/STATE/ACADEMY/`, surface prune list for
  review (never auto-delete).
- **self-improvement-swarm** — built + batched, NOT yet run. Run once as a proving pass after
  academy; route reversible intents through constitution_check.
- **D138 reconciliation** — mapped, not merged. Per-slice deploy of internal features + back-port
  live→repo; public-mode slice is Reserved. Harness-gated to arm the pipeline.
- **Bot-baseline doctrine** — CORE_DOCTRINE not yet the live bot's baseline (prod, folds into D138).
- **Loop compression #2** — event-driven build firing; churn sensor in self_audit auto-arms it if
  backlog bites.

## Learned this session

- **P9: passive rules < enforcement gates** for training-biased behavior. The whole defense-in-depth
  stack (boot pin → inject → Stop hook → learning loop).
- **3 wait-categories** (never conflate): Reserved (values) · harness-gated (tool needs your hand) ·
  large-blast-radius (schedule careful pass). I'd mislabeled harness-gate as a decision.
- **Batch heavy fan-outs** (waves of 3-4) — an 11-agent burst hits API-529. Now a protocol guardrail.
- **Render truth from a measured SSOT, never hand-type** — and fix drift at the ROOT copy
  (live-memory), because settles overwrite the repo.

---

## ALIGNMENT

**INTENT:** Make the system operate beyond base training, structurally — compressed doctrine +
named protocols every session inherits, coherence guards that kill map≠territory, enforcement
gates that beat training bias. The repertoire compounds, not just the code.

**TOP 3:**
1. ★ Land the real Academy — academy-distill re-run (batched) → CURRICULUM.md + PRUNE_MANIFEST;
   then run self-improvement-swarm once. Stream: Game/Sovereignty.
2. ★ Enforcement holds every session — P9 substrate-default gate + metric-coherence + CORE_DOCTRINE
   loaded at boot. Watch substrate_default_catches.jsonl. Stream: Game/Infrastructure.
3. ★ D138 repo≠running — per-slice reconcile (internal features autonomous; public-mode Reserved).

**BLOCKERS:** none hard. D138 arming + bot-baseline are harness-gated (James's hand when wanted).

**NEXT MOVE:** On academy-distill completion — write CURRICULUM.md + PRUNE_MANIFEST into ACADEMY/,
surface prune list; then run the swarm once and route reversible intents through constitution_check.
