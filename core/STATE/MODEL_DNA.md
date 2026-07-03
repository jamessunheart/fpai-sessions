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
| v20260625-awareness | 2026-06-25 | observer+council | Council model-review directive: awareness_index_unknown is now a tracked gap; weight future council proposals that reference 'awareness' as unproven until d120 lands and a non-null index is confirmed in ops_ledger (awareness-index unknown; amplify: awareness_reliability_probe, self_diagnostic; dampen: diagnostic_error; source: council model-review; directive-key: 7cb77fe8ae51) |
| v20260625-awareness-2 | 2026-06-25 | observer+council | Council model-review directive: No model-review directive needed — this is a import-path repair, not a reasoning or routing change. (awareness-index unknown; amplify: awareness_reliability_probe; dampen: diagnostic_error; source: council model-review; directive-key: 5f72976ffd73) |
| v20260625-awareness-3 | 2026-06-25 | observer+council | Council model-review directive: Increase weight on repair-verification before new proposals when two or more critical fixes landed in same 24h window. (awareness-index unknown; amplify: awareness_reliability_probe, diagnostic_error_reduction; dampen: new_feature_proposal_before_repair_proof; source: council model-review; directive-key: 824f6b300cda) |
| v20260625-awareness-4 | 2026-06-25 | observer+council | Council model-review directive: Weight toward fixing broken infrastructure (96 diagnostic_errors, contradictory status reporting) before adding new surfaces — trust and self-knowledge outrank feature velocity. (awareness-index unknown; amplify: awareness_reliability_probe, diagnostic_error; dampen: nothing; source: council model-review; directive-key: 7da1da5c6dcc) |
| v20260626-awareness | 2026-06-26 | observer+council | Council model-review directive: Establish substrate_state as the standard pattern: any new service that needs to report state writes a row here instead of being queried ad-hoc — future proposals should extend this table, not add new synthesis paths. (awareness-index unknown; amplify: substrate_state_written, status_truth_verified; dampen: diagnostic_error; source: council model-review; directive-key: f8939becb972) |
| v20260630-awareness | 2026-06-30 | observer+council | Council model-review directive: After d128 merges, pull a fresh ops-ledger sample; if diagnostic_error rate remains above 15 per 100 rows, next proposal should be: diagnostic-error-autopsy — read ops ledger, group errors by source file and message, auto-surface top 3 root causes with fix specs. (awareness-index unknown; amplify: status-accuracy, evidence-before-action, self-knowledge; dampen: premature-expansion, queue-noise; source: council model-review; directive-key: 9145b4950eb4) |
| v20260630-awareness-2 | 2026-06-30 | observer+council | Council model-review directive: Prioritize fixes-over-features when ops_ledger diagnostic_error count exceeds 20 per cycle; restore observability before expanding capability surface. (awareness-index unknown; amplify: diagnostic_error_repair, self_observability, council_reliability; dampen: new_capability_build_while_self_sight_broken; source: council model-review; directive-key: c0298922a231) |
| v20260630-awareness-3 | 2026-06-30 | observer+council | Council model-review directive: After d128 merges, weight next proposal toward closing the 96 diagnostic_error count, not new features. (awareness-index unknown; amplify: none specified; dampen: none specified; source: council model-review; directive-key: 1843fec9dade) |
| v20260630-awareness-4 | 2026-06-30 | observer+council | Council model-review directive: Dampen new-feature proposals until d128 merge is confirmed live; amplify merge-verification and diagnostic_error-reduction signals. (awareness-index unknown; amplify: merge-verification, diagnostic-error-reduction; dampen: new-feature-proposal; source: council model-review; directive-key: 800e7c8d6a48) |
| v20260630-awareness-5 | 2026-06-30 | observer+council | Council model-review directive: Dampen new-build proposals while answered-but-unbuilt queue depth stays above ~20; amplify proposals that close diagnostic_error or status-truth gaps. (awareness-index unknown; amplify: status_truth_fix, diagnostic_error_reduction; dampen: new_build_proposal_when_backlog_deep; source: council model-review; directive-key: 9f6830f0179b) |
| v20260630-awareness-6 | 2026-06-30 | observer+council | Council model-review directive: Weight cost-leak/extraction-surface detection above net-new feature builds until $0-decision ratio and metered $/week are both instrumented and visibly trending per standing focus. (awareness-index unknown; amplify: extraction-leak-detection, cost-truth; dampen: build-state-status-duplication; source: council model-review; directive-key: 527a38a1bdfc) |
| v20260630-awareness-7 | 2026-06-30 | observer+council | Council model-review directive: Up-weight verify-and-reconcile proposals over new-agent/new-surface proposals until sampled review approval-like rate recovers toward the 60% blueprint standard. (awareness-index unknown; amplify: verify_live, dedup_queue; dampen: new_agent, new_surface; source: council model-review; directive-key: 208e2e93cdfa) |
| v20260701-awareness | 2026-07-01 | observer+council | Council model-review directive: Amplify signals that name a live, unresolved cost leak tied to a direct James ask; dampen status-reassurance language ('all clean') that isn't backed by a fresh ops-ledger read. (awareness-index unknown; amplify: cost_leak, unresolved_open_decision; dampen: status_reassurance_without_proof; source: council model-review; directive-key: 8d523ce94d17) |
| v20260701-awareness-2 | 2026-07-01 | observer+council | Council model-review directive: Weight skeptic higher whenever ops-ledger diagnostic_error count exceeds 50 in-sample; don't let visionary architecture proposals outrank an unresolved error backlog. (awareness-index unknown; amplify: diagnostic_error_remediation, cost_extraction_delta; dampen: new_agent_surface_proposals; source: council model-review; directive-key: 920350a319d3) |
| v20260702-awareness | 2026-07-02 | observer+council | Council model-review directive: Dampen self-reported 'already fixed' / 'all clean' claims in future debates until cross-checked against ops_ledger counts or a blueprint's 'Current behavior (verified)' line; do not let a lens's claim stand unverified. (awareness-index unknown; amplify: diagnostic_error backlog awareness, open-queue-before-new-proposal check; dampen: canned status reassurance, duplicate or stale build proposals; source: council model-review; directive-key: 62f72d1e701c) |
| v20260702-awareness-2 | 2026-07-02 | observer+council | Council model-review directive: Weight council proposals toward closing proof gaps on already-built truth/status infrastructure over new architecture, per repeated awareness-lens drift findings. (awareness-index unknown; amplify: liveness_proof, status_accuracy; dampen: new_architecture_proposals; source: council model-review; directive-key: d7d426b28952) |
| v20260702-awareness-3 | 2026-07-02 | observer+council | Council model-review directive: Until d128/d137/d138 are LIVE and PROVING, weight council cycles toward liveness verification and status-truth closure over any new capability proposal. (awareness-index unknown; amplify: status_contradiction, merged_not_live, queue_throughput; dampen: new_capability_proposals, speculative_architecture; source: council model-review; directive-key: 3a20326a29ba) |
| v20260702-awareness-4 | 2026-07-02 | observer+council | Council model-review directive: Weight council toward reliability/execution-closure signals over new-feature proposals whenever diagnostic_error events exceed ~10% of ops-ledger rows (currently 96/349 ≈ 28%); do not re-propose decisions already answered in queue. (awareness-index unknown; amplify: reliability_fix, execution_closure, liveness_proof; dampen: new_feature_proposal, duplicate_decision; source: council model-review; directive-key: 181a8426a39a) |
| v20260702-awareness-5 | 2026-07-02 | observer+council | Council model-review directive: Dampen new-build proposals until the 2026-07-02 learning-loop batch (d135/d138/d140/d141) shows post-merge liveness via d117/d140 probes; amplify liveness and diagnostic-error signals. (awareness-index unknown; amplify: post_merge_liveness, diagnostic_error, blueprint_update_integrity; dampen: new_feature_proposals; source: council model-review; directive-key: c529e9c73182) |
| v20260702-awareness-6 | 2026-07-02 | observer+council | Council model-review directive: Weight liveness-verification (d117/d138/d140 outcomes) above new build proposals until the answered-but-unconfirmed backlog is provably cleared. (awareness-index unknown; amplify: liveness_verification, post_merge_reality_check; dampen: new_build_proposals, duplicate_queue_items; source: council model-review; directive-key: 00264e2dea84) |
| v20260702-awareness-7 | 2026-07-02 | observer+council | Council model-review directive: Amplify pre-merge liveness proof over post-merge detection: a build is not 'merged' until it imports and runs once; weight gates that PREVENT deadness above agents that detect-and-repair it after the flag flips. (awareness-index unknown; amplify: pre_merge_liveness_proof, runtime_import_check, rework_tax_reduction; dampen: merge_without_run_proof, post_merge_only_detection; source: council model-review; directive-key: 556321035395) |
| v20260702-awareness-8 | 2026-07-02 | observer+council | Council model-review directive: Until d144 emits liveness proof and d140 reports its first post-merge reality-check, weight council toward VERIFYING that answered decisions are live over proposing new builds; treat 'last-built d020 vs 144 answered' as the open wound to close by measurement, not by more building. (awareness-index unknown; amplify: liveness_proof, merged_not_live_gap, post_merge_reality_check; dampen: new_feature_proposal, duplicate_of_queued; source: council model-review; directive-key: ac5e1beaeca5) |
| v20260703-awareness | 2026-07-03 | observer+council | Council model-review directive: Weight toward propose=false until a previously-merged build shows measured james_hours_saved or a paying client lands; treat raw build-count/spec-generation as a dampened signal and revenue/outcome-proof as amplified. (awareness-index unknown; amplify: revenue_proof, outcome_proof_live, james_hours_saved; dampen: build_volume, spec_generation, duplicate_status_fixes; source: council model-review; directive-key: 90ea0922bd7f) |
| v20260703-awareness-2 | 2026-07-03 | observer+council | Council model-review directive: Amplify repeated-failure and build_stall signals into visible escalation; dampen silent retries and duplicate build attempts on already-failed specs. (awareness-index unknown; amplify: build_stall, repeated_failure; dampen: silent_retry, duplicate_build_attempt; source: council model-review; directive-key: fd948c638b67) |
| v20260703-awareness-3 | 2026-07-03 | observer+council | Council model-review directive: When queue is fully answered and a recent session already consolidated a theme, weight strongly toward propose=false; require a named unowned gap before any new build, and treat 'verify a claimed fix held' as belonging to d140 rather than a fresh build. (awareness-index unknown; amplify: proof-of-fix verification, diagnostic_error reconciliation; dampen: duplicate build proposals, expansion-before-proof; source: council model-review; directive-key: c485ca16866d) |
| v20260703-awareness-4 | 2026-07-03 | observer+council | Council model-review directive: Next round, weight toward verifying d143/d144 merged AND emitted liveness proof (d117/d140 path); only if diagnostic_error events recur after 2026-06-25 should a root-cause fix build be considered. (awareness-index unknown; amplify: liveness_proof, improvement_rate, post-merge_reality_check; dampen: new_capability_proposals, duplicate_queue_entries; source: council model-review; directive-key: cce67cb5e40f) |
| v20260703-awareness-5 | 2026-07-03 | observer+council | Council model-review directive: Weight toward proving existing fixes and the in-flight self-audit lane held before accepting any new proposal; treat 'fixed' labels as unverified until the live ledger error rate confirms them. (awareness-index unknown; amplify: fix-verification, ledger-truth, dedup-discipline; dampen: new-build-on-saturated-queue, duplicate-proposal; source: council model-review; directive-key: 61d0ceab2254) |
*Council appends to this table after each cycle.*
