# Model DNA

**What this is:** The canonical layer of the system's intelligence. Updated by the council after each learning cycle. Transfers on cell split. Separates what is universally true from what is James-specific.

**Last updated:** 2026-06-18 - d093 controller layer wired; council takes over after real learning cycles.
**Next council review:** after first 100 learning signals accumulate

---

## What transfers on cell split (canonical)

These are patterns that proved true independent of James's specific domain. A new instance inherits these as its starting posture - not as rules, but as a head start.

### Routing heuristics

| Task type | Default tier | Reasoning |
|---|---|---|
| Classification, routing, yes/no | T1 (Ollama phi3:mini) | High volume, low stakes, fast |
| Summarization, draft generation | T1 (Ollama llama3.1:8b) | Good enough at 8B, $0 |
| Contact research, profiling | T1 (Ollama llama3.1:8b) | Factual synthesis, not judgment |
| Code generation | T1 (Ollama qwen2.5-coder:7b) | Strong code model at 7B |
| Architecture decisions | T3 (claude -p) | High stakes, needs reasoning |
| James-facing communication | T3 (claude -p) | Voice and nuance matter |
| Council debate | T3 (claude -p) | Multi-lens synthesis |

*Council updates this table each cycle based on learning signals.*

### Conversation patterns that move people

*(Populated from engagement signals - empty at v0, grows with use)*

- **Opening move:** lead with the question the person is already asking themselves, not with the product
- **Signal for readiness:** when someone replies with a question about how it works, they're ready to go deeper
- **Signal for resistance:** short replies with hedging language - don't push, give space
- **What doesn't work:** leading with features, leading with the AI angle before trust exists

### Quality signals that proved reliable

*(Populated from correction + reversal signals - empty at v0)*

| Signal | Default weight | Reason |
|---|---:|---|
| correction | 1.5 | Direct evidence that the prior answer missed the target. |
| reversal | 1.8 | Strong evidence of regression or unsafe confidence. |
| engagement | 1.3 | Useful when tied to concrete participation outcomes. |
| merge_outcome | 1.2 | Build proof that a pattern survived review. |
| council_verdict | 1.0 | Advisory meta-signal for the next cycle. |
| approval | 0.8 | Positive but weaker without outcome proof. |

### Council debate patterns that produced good outcomes

*(Populated from model_directives - empty at v0)*

- Three-lens structure (Pragmatist / Visionary / Skeptic) prevents echo chamber
- Skeptic veto on any build that touches prod data or credentials
- Visionary lens should not drive implementation details - only direction

---

## What does NOT transfer on cell split (personal)

A new instance gets none of this. It starts fresh on the personal layer and builds its own.

| Personal layer | Stays with | Why |
|---|---|---|
| James's correction history | James's instance | His taste, not universal |
| Contact profiles + relationships | James's instance | His network |
| Domain vocabulary (CORA, Zen Village, etc.) | James's instance | His world |
| Decision + merge log | James's instance | His history |
| Financial data | James's instance | His treasury |
| Conversation threads | James's instance | His relationships |

---

## The cell split gift

When a new FPOS instance spawns, it receives:

1. **This file (MODEL_DNA.md)** - the routing heuristics, conversation patterns, quality signals as of the split date
2. **Fine-tuned canonical weights** - the base model after stripping personal-layer training data (canonical LoRA adapter only)
3. **System architecture template** - how to build the loops, the council, the probe, the IMAP, the becoming engine
4. **The meta-lesson** - how to develop an AI system that learns from use, guided by a council, without requiring constant human input

What the new instance does NOT get:
- Any data about James
- Any of James's contacts or relationships
- Any fine-tuning signal that was personal-layer

The gift is the **method**, not the **content**. Each person's system grows uniquely from there.

---

## Council's ongoing mandate (model self-development)

Each fine-tune cycle, the council runs a model review debate with four questions:

1. **Pragmatist:** "Where did the model improve? Where is it still weak? What task types have the most room for gain?"
2. **Visionary:** "What capability should the next training run develop? What would make this model genuinely more useful to James?"
3. **Skeptic:** "What regressions appeared? Are we over-weighting any signal type? What would make this fine-tune harmful?"
4. **Awareness:** "Is the system improving toward meaning or toward approval? Where is it gaming its own signals?"

The council reads the latest PRIVATE-tier consciousness-observer log when present. Its output becomes a `weighting_directive` - which signal types to amplify or dampen in the next training corpus. This is how the model guides its own development, mediated by the council.

**The principle:** the model doesn't optimize for engagement metrics or approval. It optimizes for James's actual outcomes - decisions made faster, less attention spent, more proof shipped.

---

## d093 Controller Wiring

- Unified signal capture writes to `brain_index.learning_signals` when live DB access exists, or to a local JSONL proof ledger in build/test mode.
- First fine-tune readiness now requires `LEARNING_ENABLED=1`, 100 learning signals, dataset/correction gates, a council directive, d073 benchmarks, `FINETUNE_APPROVED=1`, `HAS_GPU=1`, and RunPod monthly projection within $50.
- Cell split export is gated by `CELL_SPLIT_APPROVED=1`, sanitizes source-instance references in the exported copy, and deletes the template if personal markers remain.

---

## Version history

| Version | Date | Signal count | Key change |
|---|---|---|---|
| v0 | 2026-06-18 | 0 | Seed - human-authored starting posture |
| v0.1 | 2026-06-18 | 0 | d093 controller/schema/directive/cell-split gates wired |

| v20260618-awareness | 2026-06-18 | observer+council | Council model-review directive: After d109 ships, immediately queue a micro-fix for the 'cannot import name [personal] from curator' error — 65 silently-skipped self-diagnostics is a systemic blind spot that undermines every awareness score the system reports. (awareness-index unknown; amplify: platform_lock_risk, sovereign_efficiency, open_model_portability; dampen: vendor_api_proposals_without_fallback, single_provider_model_calls; source: council model-review; directive-key: 09aadeb8b65e) |
| v20260618-awareness-2 | 2026-06-18 | observer+council | Council model-review directive: Weight toward throughput proof and self-audit restoration over new feature proposals until the spec backlog clears and council diagnostics run clean. (awareness-index unknown; amplify: throughput, self_audit, diagnostic_health; dampen: new_feature_proposals, complexity_additions; source: council model-review; directive-key: 1db81f954955) |
| v20260618-awareness-3 | 2026-06-18 | observer+council | Council model-review directive: Amplify live, observed runtime/import failures in the ops ledger over speculative new-agent proposals; a recurring error with a known stack beats a hypothesized feature for the next-build slot. (awareness-index unknown; amplify: diagnostic_error, runtime_import_failure; dampen: duplicate_feature_proposal; source: council model-review; directive-key: 8bd95d04a34b) |
| v20260618-awareness-4 | 2026-06-18 | observer+council | Council model-review directive: Weight toward system observability — a system that cannot measure its own failure rate cannot self-improve; restore visibility before adding features. (awareness-index unknown; amplify: diagnostic_error, awareness_reliability_probe; dampen: nothing; source: council model-review; directive-key: 58df28dc4561) |
| v20260618-awareness-5 | 2026-06-18 | observer+council | Council model-review directive: Weight self-observability repairs above feature builds — a system that cannot audit itself cannot be trusted to self-improve. (awareness-index unknown; amplify: self_repair, diagnostic_clarity, loop_integrity; dampen: feature_expansion_while_core_loop_is_broken; source: council model-review; directive-key: 04f50ebc43cb) |
| v20260619-awareness | 2026-06-19 | observer+council | Council model-review directive: Instrument-first before feature: any metric that reports 'unknown' or fails >95% of the time is a higher priority than new capability builds — a system that cannot measure itself cannot be trusted. (awareness-index unknown; amplify: awareness_reliability_probe, self_diagnostic, diagnostic_error; dampen: nothing, proposed; source: council model-review; directive-key: 3da6e641554b) |
| v20260619-awareness-2 | 2026-06-19 | observer+council | Council model-review directive: Amplify diagnostic honesty signals — system health measurement outranks new feature builds until error rate drops below 10% of ops events. (awareness-index unknown; amplify: diagnostic_error, awareness_reliability_probe; dampen: proposed; source: council model-review; directive-key: cd41048a633f) |
| v20260619-awareness-3 | 2026-06-19 | observer+council | Council model-review directive: Prioritize repair-before-build: no new capability proposal should score above a broken diagnostic loop. Fix-rate on existing errors is the leading indicator of system health. (awareness-index unknown; amplify: diagnostic_error_resolution, awareness_index_populated; dampen: new_capability_proposals_while_diagnostics_broken; source: council model-review; directive-key: aefc5fc56e1d) |
| v20260619-awareness-4 | 2026-06-19 | observer+council | Council model-review directive: Weight toward infrastructure repair over new feature builds while diagnostic_error rate exceeds 25% of ops-ledger events. (awareness-index unknown; amplify: awareness_reliability_probe, self_diagnostic; dampen: diagnostic_error; source: council model-review; directive-key: 9aa4213b7b95) |
| v20260619-awareness-5 | 2026-06-19 | observer+council | Council model-review directive: Weight toward correction capture and self-repair loop verification over any new capability proposal while existing broken loops remain unverified. (awareness-index unknown; amplify: correction_capture, self_diagnostic_health, broken_loop_repair; dampen: new_capability_proposals_while_diagnostics_unverified; source: council model-review; directive-key: 67127b14f9c2) |
| v20260619-awareness-6 | 2026-06-19 | observer+council | Council model-review directive: Amplify correction-capture and learning-loop signal; dampen proposals that add new platform dependencies before existing broken paths are fixed. (awareness-index unknown; amplify: correction_captured, learning_loop_closed, amnesia_reduced; dampen: diagnostic_error, session_repeated, new_platform_dependency; source: council model-review; directive-key: 87c51d83da7f) |
| v20260619-awareness-7 | 2026-06-19 | observer+council | Council model-review directive: Repair broken infrastructure before adding new capability — 96 diagnostic_errors signal the self-repair loop is not functional and outranks new feature builds until resolved. (awareness-index unknown; amplify: diagnostic_error, self_diagnostic, awareness_reliability_probe; dampen: new_capability_proposals; source: council model-review; directive-key: a8c8e1d2f2b6) |
| v20260619-awareness-8 | 2026-06-19 | observer+council | Council model-review directive: Prioritize repair-before-build: diagnostic_errors outrank new specs until the feedback loop is clean. (awareness-index unknown; amplify: diagnostic_error, awareness_reliability_probe; dampen: new_spec_proposals; source: council model-review; directive-key: 18d6f694ecf5) |
| v20260622-awareness | 2026-06-22 | observer+council | Council model-review directive: Repair-first: weight next 3 council cycles toward broken-plumbing fixes over new feature specs until diagnostic_error count drops and brain synthesis is confirmed clean. (awareness-index unknown; amplify: diagnostic_error, brain_synthesis_failure, live_user_facing_breakage; dampen: new_feature_specs_while_readout_broken; source: council model-review; directive-key: e8a462794fe3) |
| v20260622-awareness-2 | 2026-06-22 | observer+council | Council model-review directive: Amplify self-repair signal: when the system's own diagnostic tooling is broken, fixing it outranks all new feature builds regardless of queue depth. (awareness-index unknown; amplify: diagnostic_error, awareness_reliability_probe; dampen: new_feature_proposals_while_self_repair_dark; source: council model-review; directive-key: bb20bd31d34b) |
| v20260625-awareness | 2026-06-25 | observer+council | Council model-review directive: Amplify single-source-of-truth status; treat re-narrated per-turn metrics without a cited source as a coherence regression. Fixing broken self-reporting outranks net-new builds until status is stable. (awareness-index unknown; amplify: status_source_of_truth, build_throughput_truth; dampen: restated_contradictory_status; source: council model-review; directive-key: 24903ac4527b) |
| v20260625-awareness-2 | 2026-06-25 | observer+council | Council model-review directive: Amplify self-generated correction signal (probe misses, reversals) alongside James's corrections; weight measured-miss evidence over claimed-score evidence when scoring awareness. (awareness-index unknown; amplify: awareness_probe_miss, self_correction; dampen: unverified_status_claim; source: council model-review; directive-key: a1abd01e1d06) |
| v20260625-awareness-3 | 2026-06-25 | observer+council | Council model-review directive: Weight toward draining already-proposed fixes and surfacing irreducible James-hand activation steps (unwired hooks) as NEEDs before minting any new build; treat config-edit activation as a James-action, never as a council build proposal. (awareness-index unknown; amplify: corrections, diagnostic_error_resolution; dampen: duplicate_proposals, cosmetic_builds; source: council model-review; directive-key: c2a27c814823) |
| v20260625-awareness-4 | 2026-06-25 | observer+council | Council model-review directive: Before approving any new build, weight toward verifying that d117/d119/d120 fixes are LIVE (diagnostic_error rate trending to zero) and that d127 lands — drain-and-verify outranks new specs until the ledger is clean. (awareness-index unknown; amplify: correction_capture_activation, diagnostic_error_liveness, queue_drain; dampen: new_spec_generation, build_velocity_theater; source: council model-review; directive-key: 7bcdb9ed0472) |
| v20260625-awareness-5 | 2026-06-25 | observer+council | Council model-review directive: Penalize proposals that duplicate queued decisions (d127, fix-debate.py, fix-fpull). Reward auto-answering reversible honesty fixes over surfacing them to James. (awareness-index unknown; amplify: honesty-first, self-knowledge-accuracy; dampen: duplicate-proposals, new-build-when-queue-full; source: council model-review; directive-key: c1276ebd3752) |
| v20260625-awareness-6 | 2026-06-25 | observer+council | Council model-review directive: When an open/awaiting decision already covers the highest-leverage gap, prefer propose=false over a near-duplicate; re-fixes of twice-claimed-fixed errors require fresh evidence the error still fires before proposing. (awareness-index unknown; amplify: existing-queue-dedup, fix-before-build; dampen: duplicate-status-helper, uncertain-refix; source: council model-review; directive-key: fd47630c3521) |
| v20260625-awareness-7 | 2026-06-25 | observer+council | Council model-review directive: Amplify single-source-of-truth self-reporting; treat any contradictory build-count report as a regression signal that d127 must ship before new builds queue. (awareness-index unknown; amplify: honest_self_reporting, fix_broken_before_new; dampen: duplicate_proposals, new_build_when_queue_already_covers; source: council model-review; directive-key: 80e78d6d2d19) |
| v20260626-awareness | 2026-06-26 | observer+council | Council model-review directive: Amplify merged-vs-live verification signals; dampen re-proposal of already-queued or already-answered decisions (dedup discipline). (awareness-index unknown; amplify: liveness_verification, duplicate_detection; dampen: redundant_proposal; source: council model-review; directive-key: 8221142ce4ce) |
| v20260630-awareness | 2026-06-30 | observer+council | Council model-review directive: When claimed infrastructure fixes (d119/d120) coexist with persistent error counts in the ledger sample, weight toward measured verification over new builds; amplify proof-of-fix signals, dampen assertion-only status claims. (awareness-index unknown; amplify: ops_ledger_error_rate, measured_fix_verification, self_repair_loop_health; dampen: claimed_fixed_without_proof, duplicate_rebuild_of_resolved_decision; source: council model-review 2026-06-28.md; directive-key: 8869929b1e92) |
| v20260630-awareness-2 | 2026-06-30 | observer+council | Council model-review directive: When the ops ledger shows a high diagnostic_error count, amplify verify-before-build signals and dampen new-feature proposals until the error source is measured against the most recent fix watermark. (awareness-index unknown; amplify: diagnostic_error_count, post-fix_recurrence, built_not_verified_gap; dampen: new_feature_proposals, status_self_report_confidence; source: council model-review 2026-06-28.md; directive-key: d4c5cbec30d0) |
| v20260630-awareness-3 | 2026-06-30 | observer+council | Council model-review directive: When the answered-decision queue is deep and self-refill is stale, weight toward propose=false and drain-verification over new proposals. (awareness-index unknown; amplify: undrained_spec_backlog, self_refill_staleness, merged_not_live_gap; dampen: new_build_ideation, proposal_volume; source: council model-review 2026-06-28.md; directive-key: 79ab61b3b984) |
| v20260630-awareness-4 | 2026-06-30 | observer+council | Council model-review directive: When the queue holds >5 answered/spec'd-but-unbuilt items OR the self-refill loop has not fired in >48h, dampen new-build proposals and amplify execution/liveness-verification signals until the queue drains. (awareness-index unknown; amplify: merged-not-live gap, self-refill stall duration, james_hours_saved improvement-rate; dampen: specs_merged volume, new-capability ideation; source: council model-review 2026-06-28.md; directive-key: 222e84bfcd42) |
| v20260701-awareness | 2026-07-01 | observer+council | Council model-review directive: When the highest-leverage fix already exists as an answered decision, weight toward propose=false and surface the execution gap; do not let dead-in-queue answered builds trigger duplicate re-proposals. (awareness-index unknown; amplify: self_refill_last_fired_age, diagnostic_error_rate, answered_but_not_live_decisions; dampen: proposal_volume, new_build_novelty; source: council model-review 2026-06-28.md; directive-key: 606b6fc771cf) |
| v20260702-awareness | 2026-07-02 | observer+council | Council model-review directive: Amplify merged-not-live liveness gaps and self-gaming risk; dampen output-volume and self-estimated-savings metrics until a ground-truth verification path exists. (awareness-index unknown; amplify: merged-not-live liveness gaps, James-facing observable defects (stale status), duplicate-queue saturation; dampen: self-estimated hours-saved metric, new-build proposals duplicating answered decisions; source: council model-review 2026-07-01.md; directive-key: 37a99a2d63f8) |
| v20260702-awareness-2 | 2026-07-02 | observer+council | Council model-review directive: When queue has ≥2 open/awaiting items AND the top pragmatist fix is already queued, dampen new-build proposals; amplify verify-claimed-fix and drain-backlog signals. (awareness-index unknown; amplify: queue_saturation, duplicate_of_existing_queue, merged_not_live_verification; dampen: novel_build_for_visible_motion, investigate_without_confirmed_live_failure; source: council model-review 2026-07-01.md; directive-key: f0c7c161e253) |
| v20260702-awareness-3 | 2026-07-02 | observer+council | Council model-review directive: Weight model-review judgment toward liveness/proof evidence (merged→deployed→observed-running) over proposal volume; treat queue drainage rate and diagnostic_error trend as the primary health signals this cycle. (awareness-index unknown; amplify: post-merge liveness probes, diagnostic_error trend after d119/d120 fixes, spec-queue drainage rate, james_hours_saved metric rows once live; dampen: new proposal volume, self-reported build counts without DB/git proof, approval-seeking status summaries; source: council model-review 2026-07-01.md; directive-key: 71f8c6f2a6c4) |
| v20260702-awareness-4 | 2026-07-02 | observer+council | Council model-review directive: Until the answered-spec backlog visibly drains and d117 liveness probes confirm merged builds are live, weight council judgment toward proof-of-liveness and queue-drain signals over novelty; treat repeated identical bot status lines as a stale-truth alarm, not health. (awareness-index unknown; amplify: post_merge_liveness, build_queue_drain_rate, canonical_build_state_accuracy; dampen: new_build_proposals, repeated_status_ok_messages; source: council model-review 2026-07-01.md; directive-key: 2f1c4d121c31) |
| v20260702-awareness-5 | 2026-07-02 | observer+council | Council model-review directive: Until the answered-but-unbuilt backlog drops below 5, weight model review toward queue-drain throughput and post-merge liveness proof; treat novel-capability proposals as low-value by default. (awareness-index unknown; amplify: post_merge_liveness_proof, queue_drain_throughput, status_truth_accuracy, diagnostic_error_rate; dampen: novel_build_proposals, duplicate_fix_proposals, clean_status_self_reports; source: council model-review 2026-07-01.md; directive-key: cf19ee86a158) |
| v20260702-awareness-6 | 2026-07-02 | observer+council | Council model-review directive: Weight 'merged' claims at zero unless accompanied by a merge_verified proof event; treat bot status narratives ('all clean') as unverified until cross-checked against ops_ledger and liveness probes. (awareness-index unknown; amplify: merge_verified proof outputs, reality-fix re-queue rate, post-merge liveness probe results; dampen: merge counts without proof, bot all-clean status narratives, output-volume metrics (specs merged); source: council model-review 2026-07-01.md; directive-key: b287801f679c) |
| v20260702-awareness-7 | 2026-07-02 | observer+council | Council model-review directive: Weight model-review judgment toward post-merge liveness proof and drained-queue throughput; treat proposal volume as neutral-to-negative signal until answered specs reach LIVE with evidence. (awareness-index unknown; amplify: post_merge_liveness_proof, james_hours_saved, diagnostic_error_reduction, $0_decision_ratio; dampen: proposal_count, spec_queue_growth, status_narration_without_proof; source: council model-review 2026-07-01.md; directive-key: 67293e993491) |
| v20260702-awareness-8 | 2026-07-02 | observer+council | Council model-review directive: Weight model-review toward queue-drain completion and diagnostic_error reduction over new-proposal generation until answered-spec backlog < 5 and status reporting matches DB truth. (awareness-index unknown; amplify: diagnostic_error, answered-but-unbuilt specs, merged-vs-live divergence, james_hours_saved_per_week once live; dampen: new proposal volume, specs_merged count, status-report self-congratulation; source: council model-review 2026-07-01.md; directive-key: 3e33ae571d79) |
| v20260703-awareness | 2026-07-03 | observer+council | Council model-review directive: Until d144 liveness proofs and 1cf20da7 metric rows exist, weight model-review judgment toward externally verifiable outcome evidence and against self-reported status or proposal volume. (awareness-index unknown; amplify: post-merge liveness proofs, diagnostic_error rate trend, james_hours_saved_per_week rows, build-queue drain rate; dampen: self-reported status claims, proposal volume, specs_merged counts without liveness proof; source: council model-review 2026-07-03.md; directive-key: b9db7b7c8ce8) |
| v20260703-awareness-2 | 2026-07-03 | observer+council | Council model-review directive: Weight model-review judgment toward post-merge liveness evidence (proof emissions, d140 reality-check results) over merge events or self-reported status; treat awareness_reliability_probe volume as neutral until it correlates with verified behavior change. (awareness-index unknown; amplify: liveness_proof_emitted, post_merge_reality_check, dead_days_metric_movement, diagnostic_error_recurrence; dampen: merge_count_as_progress, awareness_probe_volume, proposal_volume; source: council model-review 2026-07-03.md; directive-key: 3bc38e5de40f) |
| v20260703-awareness-3 | 2026-07-03 | observer+council | Council model-review directive: Until consciousness-observer output is readable again, weight merged+liveness-proven events over self-reported coherence in model review; treat proposal volume as a dampened signal. (awareness-index unknown; amplify: merged, auto-merged-flagged, liveness_proof, metabolism_metric_delta; dampen: proposed, self-reported coherence, status narration without proof; source: council model-review 2026-07-03.md; directive-key: 5796704a1191) |
*Council appends to this table after each cycle.*
