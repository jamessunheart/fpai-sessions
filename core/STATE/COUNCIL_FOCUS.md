# STANDING COUNCIL FOCUS — the merged→live deploy bridge (set by James 2026-06-15)

## Primary weight directive

Read `core/STATE/NORTH_STAR.md` before proposing the next build. Weight council debate toward the North Star:
outperform well-funded AI players on capital and hardware efficiency in sovereign environments.

The current concrete proof targets are:
- `cost_per_task_vs_gpt4o_api`
- `latency_p95_ms`
- `hardware_cost_per_1k_tasks`
- `sovereign_run`

The unified memory directive remains active alongside this: preserve the memory/proof loop so shipped work, benchmark results, and council decisions return as routing intelligence instead of isolated artifacts.

Council JSON should cite `NORTH_STAR.md` whenever a proposed build claims to improve sovereign efficiency, benchmark proof, local/open-model capability, or the build-to-live loop that lets those improvements matter.

**Weight every proposal toward designing the GATED build→deploy bridge.** This is the current
keystone and directly serves the North Star (FPOS advances WITHOUT James prompting).

## The problem
The autonomous loop builds + reviews + **auto-merges** AI-approved safe builds into the build repo
(`/opt/fpai-build/FPAI_Cockpit`, branch `feat/headless-build`). But the **running systems are deployed
separately** — e.g. the live bot at `/opt/sh-brain-src`. So **merged ≠ live**: self-improvements
accumulate in a staging branch and never reach the running system. The loop *looks* productive
(builds N/day) while the live system doesn't actually change. This makes self-evolution theatrical
where it matters most.

## What to design
A **gated deploy step** that takes an auto-merged, AI-reviewed, SAFE change → deploys it to the
correct live target → safely. It must include:
- **Target mapping** — which built paths map to which live system (e.g. `SERVICES/sunheart-brain/curator/*` → `/opt/sh-brain-src/curator/`).
- **Backup before deploy** (`.bak-*` / git ref) + **automatic rollback** on failure.
- **Pre-deploy verification** — `py_compile` / import-check / smoke-test before the service restart counts as success.
- **Post-deploy health check** + auto-revert if the service fails to come up.
- **Hard exclusions** — NEVER auto-deploy anything touching credentials, treasury/money writes, or irreversible deletes; those surface to James.
- **Reversibility** — every deploy reversible from the phone (`reverse dNNN`-style).
- **Respect the harness wall** — the harness hard-blocks agent self-escalation; the bridge must run as authorized server infra, not by an agent self-granting.

## Constraints / non-negotiables
- $0 marginal (subscription CLIs only). Small blast radius. Guardrail + proof + rollback on every deploy.
- The self-modifying build loop stays operator-only (single-tenant); this is NOT for multi-tenant.
- Start with the SMALLEST safe slice (e.g. deploy only `curator/*` bot modules) and prove it before generalizing.

## Deliverable
Propose ONE concrete build spec for the smallest safe, reversible, verifiable version of this bridge.
