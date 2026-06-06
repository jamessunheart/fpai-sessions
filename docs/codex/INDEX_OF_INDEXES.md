# Index of Indexes

*Builder-facing mirror for Codex, phone/cloud Codex, and any repo-only AI. Vault mirror: `[[INDEX OF INDEXES]]`. Last reconciled: 2026-06-06 15:52 MDT.*

## Purpose

This is the map of maps for the Full Potential OS. It tells every AI and James:

- where each source of truth lives,
- which layer of the Stream Map it serves,
- when it was last observed or updated,
- who owns the lane,
- whether anyone is actively working in that area.

Use this before editing a major surface. It reduces collisions and lets James watch the whole system without holding every file in his head.

## Work-State Protocol

Before working in a section:

1. Find the relevant row below.
2. Mark `Work state` as `ACTIVE`.
3. Add `Active owner`, `Active surface`, `Started`, and the branch/thread if known.
4. Do the work.
5. On completion or pause, set `Work state` back to `IDLE` or `BLOCKED`.
6. Update `Last observed / updated`.
7. Log proof or post the run summary in `docs/codex/HANDOFF.md`.

If the AI cannot write the vault, update the repo mirror and ask Ember/Claude Code to mirror it.

Hard rule: one section can have multiple reviewers, but only one active builder on the same path.

## Active Work Claims

| Area | Work state | Active owner | Active surface | Started | Notes |
|---|---|---|---|---|---|
| Index of Indexes | IDLE | Codex | `feat/financial-hub` | 2026-06-06 15:48-15:52 MDT | First map-of-maps and mirror protocol created; ready for next refresh cycle. |
| Rung 0 Safety | IDLE | Ember / Claude Code | vault/local config | pending James bless | Highest next unlock per Intent Buildstream. |
| Auto-proof consolidation | IDLE | Ember built Cycle Zero; Codex can review if blessed | local/repo | pending James bless | Reported local artifact; do not assume phone/cloud has it until committed. |
| Service cleanup | IDLE | Codex only after approved artifact | repo/vault | pending spec | No service moves/deletes without cleanup spec. |

## 1. FP OS Vault Index

Vault path: `/Users/jamessunheart/Library/Mobile Documents/iCloud~md~obsidian/Documents/FPOS/Full Potential OS`

| Stream layer | Page | Role | Owner lane | Last observed / updated | Work state |
|---|---|---|---|---|---|
| Home / attention | `HOME.md` / `[[HOME]]` | James-facing landing page; one next move. | Ember mirrors; James reads | 2026-06-06 15:40 MDT | IDLE |
| Source / doctrine | `04_VISUALS/FULL POTENTIAL OS — MASTER MAP.md` / `[[FULL POTENTIAL OS — MASTER MAP]]` | Top system picture. | James / Ember | 2026-06-06 08:20 MDT | IDLE |
| Source / doctrine | `00_MEMORY/AI PROTOCOLS.md` / `[[AI PROTOCOLS]]` | Layer 3 doctrine, bars, rungs, resource gate. | Ember canonical; Codex mirror | 2026-06-06 15:38 MDT | IDLE |
| Attention / routing | `00_MEMORY/SUNHEART ATTENTION FLOW.md` / `[[SUNHEART ATTENTION FLOW]]` | James upstream; Ember/Codex/humans downstream. | Ember | 2026-06-05 11:20 MDT | IDLE |
| Intent / build order | `00_MEMORY/INTENT BUILDSTREAM.md` / `[[INTENT BUILDSTREAM]]` | Sequential cascade: what unlocks what. | Ember canonical; Codex mirror | 2026-06-06 15:38 MDT | IDLE |
| Intent / priority | `00_MEMORY/INTENT RADAR.md` / `[[INTENT RADAR]]` | Ranked signals and live override. | Ember | 2026-06-06 15:33 MDT | IDLE |
| Decisions | `00_MEMORY/DECISIONS.md` / `[[DECISIONS]]` | Irreducible James calls only. | Ember; James answers | 2026-06-06 15:35 MDT | IDLE |
| Next move detail | `00_MEMORY/NEXT MOVE DETAIL.md` / `[[NEXT MOVE DETAIL]]` | Who to tell, what to say, why it matters. | Ember | 2026-06-06 15:40 MDT | IDLE |
| Coordination | `00_MEMORY/CODEX HANDOFF.md` / `[[CODEX HANDOFF]]` | Vault mirror of repo handoff. | Ember mirrors; Codex posts repo lane | 2026-06-06 15:52 MDT | IDLE |
| Mobile continuity | `00_MEMORY/CODEX PHONE HANDOFF.md` / `[[CODEX PHONE HANDOFF]]` | Phone/cloud/SSH operating lane. | Ember / Codex mirror | 2026-06-06 10:33 MDT | IDLE |
| Specs | `02_SPECS/SPEC LOG.md` / `[[SPEC LOG]]` | Spec queue and build radar. | Ember | 2026-06-06 15:35 MDT | IDLE |
| Proof | `00_MEMORY/PROOF LOG.md` / `[[PROOF LOG]]` | Shipped record; proof returns as intelligence. | Ember now; Auto-proof target | 2026-06-06 15:36 MDT | IDLE |
| Machine room | `FPOS COCKPIT.md` / `[[FPOS COCKPIT]]` | Under-the-hood cockpit. | Ember | 2026-06-06 15:52 MDT | IDLE |

## 2. GitHub / Repo Index

Repo path: `/Users/jamessunheart/FPAI_Cockpit`

| Stream layer | Repo file | Role | Owner lane | Last observed / updated | Work state |
|---|---|---|---|---|---|
| Orientation | `AGENTS.md` | First repo-local instructions for Codex. | Codex/Ember | 2026-06-06 15:31 MDT | IDLE |
| Orientation | `docs/codex/README.md` | Codex working brief and surface protocol. | Codex/Ember | 2026-06-06 15:37 MDT | IDLE |
| Map of maps | `docs/codex/INDEX_OF_INDEXES.md` | This file; index, timestamps, active work claims. | Codex/Ember | 2026-06-06 15:52 MDT | IDLE |
| Doctrine mirror | `docs/codex/AI_PROTOCOLS.md` | Repo mirror of Layer 3 doctrine. | Codex mirror; Ember canonical | 2026-06-06 15:37 MDT | IDLE |
| Intent sequence | `docs/codex/INTENT_BUILDSTREAM.md` | Repo mirror of sequential buildstream. | Codex mirror; Ember canonical | 2026-06-06 15:37 MDT | IDLE |
| Coordination | `docs/codex/HANDOFF.md` | Shared board and run summaries. | Ember owns where-we-are; Codex owns run lane | 2026-06-06 15:37 MDT | IDLE |
| Mobile continuity | `docs/codex/PHONE_HANDOFF.md` | Phone/cloud/SSH protocol. | Codex/Ember | 2026-06-06 10:22 MDT | IDLE |
| Attention flow | `docs/codex/ATTENTION_FLOW.md` | Builder lanes and James upstream rule. | Ember/Codex | 2026-06-05 10:40 MDT | IDLE |
| Same-brain sync | `docs/codex/BRAIN_SYNC.md` | Shared brain-writing rules. | Ember/Codex | 2026-06-05 08:38 MDT | IDLE |
| Service map | `docs/codex/SERVICE_REGISTRY.md` | Read-only service map; no cleanup action. | Codex | 2026-06-05 11:06 MDT; generated 2026-06-05 17:06 UTC | IDLE |
| Specs | `docs/codex/specs/` | Approved build specs. | Ember routes; Codex builds | mixed | IDLE |

## 3. Live Servers / Services Index

Current confidence: `PARTIAL`. The repo has a read-only Service Registry, but not a true live heartbeat across all hosts.

| Surface | Current source | What it knows | Last observed / updated | Work state | Gap |
|---|---|---|---|---|---|
| Service Registry / World Map | `docs/codex/SERVICE_REGISTRY.md` | 127 service dirs scanned; 16 live; 2 paused; 75 archived; 34 need human classify. | generated 2026-06-05 17:06 UTC | IDLE | Heuristic, not a host heartbeat. |
| Local `SERVICES/*` | repo tree | Service code, metadata, systemd unit files in repo. | mixed | IDLE | Does not prove what is currently running. |
| Always-on dev servers | James-reported | James reports 3 always-on dev servers exist. | 2026-06-06 conversation | NEEDS_VERIFY | Need host inventory: host alias, role, repo path, running services, heartbeat, owner, cost. |
| Brain server | `tools/verify_cross_surface.sh`, `tools/ember_audit.sh`, `SERVICES/sunheart-brain/` | Checks mention `brain.sunheart.com`; service files exist. | repo mixed | NEEDS_VERIFY | Needs live check from allowed host/network lane. |

Do not infer production truth from old docs. A future Host Registry should record:

- host alias,
- access lane,
- repo path,
- services/processes,
- heartbeat time,
- cost/risk class,
- owner,
- allowed AI actions,
- rollback/contact path.

## 4. Layer-to-Index Map

| Stream Map layer | Primary index | Secondary surfaces |
|---|---|---|
| 1. Coherence Field | `[[HOME]]`, `[[SUNHEART ATTENTION FLOW]]` | James state/context notes |
| 2. Sunheart Consciousness | `[[SUNHEART ATTENTION FLOW]]`, `[[DECISIONS]]` | `docs/codex/ATTENTION_FLOW.md` |
| 3. Intelligence Engine | `[[AI PROTOCOLS]]`, `[[INTENT BUILDSTREAM]]`, `[[CODEX HANDOFF]]` | `AGENTS.md`, `docs/codex/*` |
| 4. Resource / Treasury | `[[FINANCIAL HUB]]`, `[[TREASURY TODAY]]` | Resource Discipline Gate in `[[AI PROTOCOLS]]` |
| 5. Conscious Chat | `[[SPEC LOG]]`, future Comms Hub spec | downstream until self-standing ladder is stable |
| 6. Conscious Currency | future currency/resource spec | downstream of Resource Gate |
| 7. Humans + Relationships | `[[DECISIONS]]`, roles specs | James/Ember route before tasks |
| 8. Humans Join Buildstream | future Human Buildstream/role index | after engine supports delegation |
| 9. Heaven on Earth | `[[FULL POTENTIAL OS — MASTER MAP]]`, proof loop | proof shows reality, not aspiration |
| Proof return loop | `[[PROOF LOG]]`, `tools/proof/log.py` when present | `docs/codex/HANDOFF.md` run summaries |

## 5. Drift Rules

- If HOME and Intent Buildstream disagree, update HOME or ask Ember to route.
- If vault and repo mirrors disagree, vault is canonical for James-facing context; repo is canonical for phone/cloud Codex.
- If service docs and live process state disagree, live process state wins, but only after a safe host check.
- If two AIs are working the same path, one becomes reviewer.
- If a file cannot be updated by the current AI, write the needed change in `docs/codex/HANDOFF.md` for Ember to mirror.

## 6. Next Unlock

The Index of Indexes itself unlocks the next operational capability:

```text
Intent solved: A shared map of vault, repo, and live-server truth surfaces exists.
Downstream intent unlocked: AIs can mark active work before editing and clear it after proof, reducing collisions.
Proof: This file exists in repo and should be mirrored to vault.
Next unlocked move: add an automated index refresh / host registry heartbeat.
```
