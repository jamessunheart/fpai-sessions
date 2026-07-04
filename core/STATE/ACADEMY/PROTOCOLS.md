# PROTOCOLS — the system's named orchestrations & rituals

_A living registry. Every session should know these exist, invoke them when they fit, and
**invent + name new ones** that enhance the system's intent. This is how the system's
operating repertoire compounds — not just its code, but its *ways of working*._

> A **protocol** is a named, repeatable way the system acts on itself or the world:
> an autonomous loop, an enforcement gate, a multi-agent orchestration, or a compiler.
> Naming it makes it discoverable, invocable, schedulable, and improvable.

---

## The registry (as of 2026-07-03)

### 🔥 Autonomous loops (scheduled; self-run, laptop-free, $0 via subscription CLIs)
| Protocol | What it does | Cadence | Where |
|----------|-------------|---------|-------|
| **Council Fire** | Multi-lens debate on surfaced intents → proposes THE one build | 20 min (change-gated) | `tools/council/debate.py` · `fpai-council.timer` |
| **RCA Reflex** | Error → 5-whys root → BUG_LOG → graduates to a Principle | 2 h | `tools/rca/autonomous_rca.py` · `fpai-rca.timer` |
| **Nightly Metabolism** | Allocates the next experiment to the weakest conversion (Law 4) | nightly | `tools/metabolism/nightly.py` · `fpai-nightly-metabolism.timer` |
| **Self-Audit** | Allocation audit of our own stack + coherence gate + recompiles doctrine | daily 04:00 | `tools/allocation/self_audit.py` · `fpai-self-audit.timer` |
| **Awareness Probe** | Measures bot context-reliability → `awareness_reliability.json` SSOT | hourly | `tools/awareness/reliability_probe.py` |

### 🚪 Enforcement gates (hooks / checks — enforce at the moment of risk)
| Protocol | What it enforces | Where |
|----------|-----------------|-------|
| **Substrate-Default Gate** | Blocks the trained default-to-James bias unless a Reserved class is named (P9) | `.claude/hooks/check-substrate-default.sh` |
| **Metric Coherence Guard** | Reported prose must match the measured SSOT (kills map≠territory drift) | `tools/governance/metric_coherence.py` |
| **Structural Coherence Guard** | Created truth must propagate — every principle reaches the boot pack, no dangling tool/hook pointers | `tools/governance/coherence_invariants.py` |
| **Constitution Check** | Screens proposals against the 8 Laws before they queue | `tools/governance/constitution_check.py` |
| **Guard Adjudicator** | On hitting a block, debate REAL-gate vs my-timidity → reframe+TEST, or solidify+route legitimately (safety-biased; never evades an enforced gate) | `tools/governance/guard_adjudicator.py` |
| **Collision Guard** | Stops parallel sessions bundling each other's uncommitted edits | `.claude/hooks/check-collision.sh` |

### 🐝 Orchestration workflows (multi-agent swarms; on-demand + schedulable)
| Protocol | What it does | Invoke |
|----------|-------------|--------|
| **Academy Distill** | Team of Sonnets melts the whole corpus → compressed Academy + prune manifest | `Workflow({name:'academy-distill'})` |
| **Self-Improvement Swarm** | Probe swarm finds weak points → answer swarm adversarially diagnoses → weighted intent stream → build queue | `Workflow({name:'self-improvement-swarm'})` |

### 🛠️ Compilers (render truth from source; never hand-typed)
| Protocol | What it does | Where |
|----------|-------------|-------|
| **Compile Doctrine** | Auto-generates `CORE_DOCTRINE.md` (compressed education) from canonical sources | `tools/academy/compile_doctrine.py` |
| **Academy Distill (proofs)** | Distills proofs/corrections/outcomes → `ACADEMY.md` | `tools/academy/distill.py` |

_(Naming tradition: the **Command Constellation** — Compass · Lantern · Maproom · Gate · Bridge ·
Forge · Mirror · Root · Watchfire · Healer · Council Fire · Instrument Rack · Proof River · Loop.
See `reference_command_constellation`. New protocols should fit this evocative-naming spirit.)_

---

## How to invent a new protocol (any session may do this)

The system compounds when sessions add not just fixes but new *ways of working*. To coin one:

1. **Find the intent it serves.** It must advance the spine — Allocation Intelligence toward
   max Future Capability. If it doesn't make the system more capable/coherent, don't build it (Law 8).
2. **Name it evocatively** in the Command Constellation spirit — a name that says what it *is*
   at a glance (Council Fire, Whetstone, Crucible…). The name is the interface.
3. **Define its shape:** trigger (event / cadence / on-demand) · steps or agents · output ·
   the ONE proof it produces. Prefer the cheapest-sufficient carrier (Intelligence Economy).
4. **Bake in the guardrails** (non-negotiable): reversible-first · small blast radius ·
   read-cap on any swarm · **batch heavy fan-outs into waves of 3-4** (a big parallel burst
   hits API-529 overload — an 11-agent burst once killed 10/11 mid-run; use an `inBatches`
   helper) · **output-only if it would arm a pipeline** (queuing to the build DB is
   harness-gated — route through Constitution Check, don't self-arm) · a kill-switch.
5. **Build it** as a `Workflow` script in `.claude/workflows/`, a tool + timer, or a hook.
6. **Register it here** — add a row so future sessions discover it. An unregistered protocol
   is invisible; registration is the compounding step.
7. **Prove it once, then schedule** only if it demonstrably compounds value (persistence =
   James-enable, harness-gated). Measure cost-per-useful-PROOF, not activity.

> A protocol that isn't registered here didn't fully happen. Coin boldly, name well, register always.
