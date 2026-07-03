# SSOT REGISTRY — where every kind of truth lives

**Created:** 2026-06-12 (session f98f2f16, system-organization review)
**The rule:** every fact-domain has exactly ONE canonical source. Everything else is a mirror that may lag. When two surfaces disagree, the canonical column wins — full stop. Before asserting any fact, check its row; before writing a fact, write it to the canonical source FIRST, mirrors second (or let sync tools mirror it).
**Enforced by:** memory-recall hook surfaces this registry's domain on matching prompts · `tools/memory/build_system_map.py` flags stale SSOTs · siblings read this before claiming state.

---

## The registry

| Fact domain | CANONICAL source | Mirrors (may lag) | Freshness contract |
|---|---|---|---|
| **Founder priorities / the ONE thing** | `core/STATE/NOW.md` | vault `[[NOW MIRROR]]` · `/opt/fpai/NOW.md` on servers (🔴 known 2mo stale — do not trust) · `@sunheartbrain_bot /goals` | ≤7 days or flagged |
| **Live build queue** | vault `[[BUILDSTREAM BOARD]]` + `[[INTENT BUILDSTREAM]]` | `docs/codex/INTENT_BUILDSTREAM.md` | per CONVERGENCE.md: NOW.md is NOT the live queue |
| **AI working goals** | `core/STATE/AI_GOALS.md` 🟡 (stale since 2026-05-08 — refresh or demote) | vault `[[GOALS MIRROR]]` · qb books | ≤14 days |
| **Treasury actuals ($)** | `~/.config/fpai/treasury/treasurer_resources_<latest>.md` | vault `[[TREASURY TODAY]]` `[[FINANCIAL RESOURCES]]` · `SERVICES/unified-financial-dashboard/manual_financial_inputs.json` | snapshot ≤14 days; NEVER in repo (schema only: `TREASURY_SCHEMA.md`) |
| **Treasury positions (live deltas)** | memory `project_treasury_open_positions.md` | — | write THIS TURN on any move |
| **Asset inventory (domains, equity, bullion)** | treasury snapshot "Digital Assets" + equity sections | vault `[[RESOURCE INVENTORY]]` | with snapshot |
| **Server / fleet live state** | **the servers themselves** · cached: `core/STATE/FLEET_SNAPSHOT.md` | `docs/codex/HOST_REGISTRY.md` · `SERVICE_REGISTRY.md` · memory fleet notes | snapshot ≤14 days; live-read before infra work (probe-before-assume) |
| **Service catalog (what code exists)** | `docs/codex/SERVICE_REGISTRY.md` (generated) | vault `[[SERVICE REGISTRY — SORTED]]` | regenerate on service add/remove |
| **Who James is / operating rules** | `core/STATE/JAMES_CANONICAL.md` + `AI_CHARTER.md` | — | stable; edit on James correction only |
| **Ember identity** | `~/.claude/.../memory/identity/` stack | `core/STATE/identity/` (repo mirror via sync script) | settle ritual |
| **Episodic + feedback memory** | `~/.claude/.../memory/*.md` (305 files) | — | auto-recall hook surfaces per prompt |
| **Vault knowledge (concepts, mindmaps, doctrine)** | `~/Documents/FPOS/Full Potential OS/` (🔵 NOW LOCAL GIT — migrated off iCloud 2026-06-12) | brain server semantic store | vault `tools/index/refresh.py` keeps its own index |
| **Cross-session coordination** | `core/BUILD/SESSION_NOTES/` + `core/STATE/convergence/<date>/` | `docs/codex/HANDOFF.md` · `docs/coordination/handoffs/` | one note per session before close |
| **Human-gate decisions** | `core/STATE/HUMAN_EDGE_QUEUE.json` | HUMAN_EDGE_QUEUE.md render | update on gate open/close |
| **Credentials / tokens** | `~/.config/fpai/<service>/` + servers' `/opt/fpai/api_keys.json` | — | NEVER in repo or vault; pointers only |
| **Costs** | `~/.config/fpai/cost/` + vault `[[COST LEDGER]]` | memory `project_costs.md` | ≤30 days |
| **Legal / entity state** | `core/STATE/LEGAL_STATE_ASSESSMENT_<date>.md` | vault 508c1a/White Rock concept pages | on event |
| **Fundraising architecture** | `core/STATE/PATRON_ENGINE.md` + `CORA_NATION_FRONT_DOOR.md` | — | 🔴 Counsel gates before publish |
| **Bot awareness reliability (metric)** | `core/BUILD/signals/awareness_reliability.json` (measured every probe) | NOW.md · HOT_STATE · ALIGNMENT.md prose (🔴 hand-typed → drifts; cite JSON, don't type) | guarded by `tools/governance/metric_coherence.py` (runs in daily self-audit) |
| **Running bot code** | live `/opt/sh-brain-src/curator/tgbot.py` (server 162, `sh-brain-tgbot`) | `SERVICES/sunheart-brain/curator/tgbot.py` (🔴 KNOWN-FORKED both ways — see `core/BUILD/reconciliation/D138_tgbot_repo_vs_live.md`) | repo ≠ running until D138 per-slice merge |

## Conflict resolution (extends INDEX_OF_INDEXES drift rules)

1. Live system state beats any document. Documents record; reality rules.
2. Within documents: the CANONICAL column beats every mirror.
3. Between laptop repo and servers: laptop repo wins for intent/priorities; servers win for runtime truth.
4. Between vault and repo: vault is canonical for James-facing doctrine/knowledge; repo for operational state and anything phone/cloud Codex needs.
5. A fact older than its freshness contract is a QUESTION, not a fact — verify before asserting (probe-before-assume).

## Known drift to fix (as of 2026-07-03)

- ☐ **D138: repo tgbot ≠ running bot** (bidirectional fork — 16 built-not-deployed fns, 12 live-not-committed fns) → per-slice reconcile via `deploy_curator_slice.sh`; map at `core/BUILD/reconciliation/D138_tgbot_repo_vs_live.md`
- ✅ metric drift (awareness 100%/88%/41.3% across files) → `metric_coherence.py` guard now catches it, wired into daily self-audit

- ☐ `docs/codex/INDEX_OF_INDEXES.md` §1 still points at the dead iCloud vault path → update to `~/Documents/FPOS/Full Potential OS` (file dirty from sibling session — integration session applies)
- ☐ `core/STATE/AI_GOALS.md` stale since 2026-05-08 → refresh or formally mark vault BUILDSTREAM as successor
- ☐ `ASSEMBLY_LINE.md` (2025-11-25) + `/opt/fpai/BOOT.md` (2025-11-17) → archive
- ☐ `MEMORY.md` memory index is 40KB and truncates on load → slim to pointers (auto-recall now carries the load)
