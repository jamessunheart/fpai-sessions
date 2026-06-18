# SCOUT REPORT

**Date:** 2026-06-18
**Focus:** sovereign local-first model and tool replacements
**Mode:** local deterministic seed scan; no network; no installs; no external spend.

## One Recommended Next Upgrade

**Service Registry / World Map** -> **build**

**Why:** Directly answers the current system problem: the substrate cannot optimize what it cannot see.
**Next step:** Generate a read-only service inventory from SERVICES/* metadata, then manually classify live/paused/archive.
**Caution:** Avoid broad automated edits; produce a report first, then route cleanup specs.

## Scored Intent

- **Intent:** Service Registry / World Map
- **Verdict:** build
- **Score:** 22
- **Route:** Codex spec before implementation; James approves consequential changes.
- **Definition of done:** Generate a read-only service inventory from SERVICES/* metadata, then manually classify live/paused/archive.

## Candidates

| Score | Candidate | Category | Verdict | Sovereignty | Cost | Hits |
|---:|---|---|---|---|---:|---|
| 22 | Service Registry / World Map | system clarity | build | Hybrid | 1 | local |
| 14 | LiteLLM / OpenRouter-style Model Router | model routing | API | Hybrid | 5 | model |
| 13 | Actual Budget | financial dashboard | API | Hybrid | 5 | first, local |
| 12 | Obsidian Agent Skills | second brain | fork | Hybrid | 4 | - |
| 12 | n8n | workflow automation | API | Hybrid | 4 | - |
| 11 | Microsoft Conductor | agent orchestration | fork | Hybrid | 6 | - |
| 9 | Graphiti / Temporal Knowledge Graph | knowledge graph | fork | Hybrid | 7 | - |
| 8 | Open WebUI | AI interface | ignore | Hybrid | 4 | local, model |
| 6 | Dify / Flowise | agent app builder | ignore | Hybrid | 5 | tool |

## Candidate Notes

### Service Registry / World Map
- **Summary:** A canonical local registry of services, status, owner, URLs, deploy target, cost, and kill condition.
- **Fit:** Directly answers the current system problem: the substrate cannot optimize what it cannot see.
- **Sovereignty:** Hybrid — sovereignty posture unclear from available metadata. Require an explicit open-source/self-hostability check before adoption.
- **Next step:** Generate a read-only service inventory from SERVICES/* metadata, then manually classify live/paused/archive.
- **Caution:** Avoid broad automated edits; produce a report first, then route cleanup specs.
- **Source:** local need; existing SERVICES/INDEX.md is stale

### LiteLLM / OpenRouter-style Model Router
- **Summary:** A thin routing layer for model choice, budgets, caps, and provider fallback.
- **Fit:** Good fit after cost meter is trustworthy; lets expensive calls route by task class.
- **Sovereignty:** Hybrid — sovereignty posture unclear from available metadata. Require an explicit open-source/self-hostability check before adoption.
- **Next step:** Add a read-only routing recommendation report before using any paid provider.
- **Caution:** Requires secrets and spend controls; never auto-wire providers from scout output.
- **Source:** known ecosystem pattern

### Actual Budget
- **Summary:** Local-first finance tracking and budgeting system.
- **Fit:** Potential fit for treasury visibility, but not the current clarity bottleneck.
- **Sovereignty:** Hybrid — sovereignty posture unclear from available metadata. Require an explicit open-source/self-hostability check before adoption.
- **Next step:** Evaluate after financial consolidation hub spec is active.
- **Caution:** Do not import sensitive financial data during scout phase.
- **Source:** known ecosystem tool

### Obsidian Agent Skills
- **Summary:** Skill-style workflows attached to an Obsidian vault and reused by agents.
- **Fit:** Strong fit for FPOS because James already uses the vault as visible memory.
- **Sovereignty:** Hybrid — sovereignty posture unclear from available metadata. Require an explicit open-source/self-hostability check before adoption.
- **Next step:** Fork the pattern into one repo-local skill for scout reports and proof logs.
- **Caution:** Do not let skill proliferation become another unindexed surface.
- **Source:** approved scout target from docs/codex/README.md

### n8n
- **Summary:** Workflow automation engine with many connectors and human-readable flows.
- **Fit:** Useful for boring repeatable tasks after routing and permission boundaries are firm.
- **Sovereignty:** Hybrid — sovereignty posture unclear from available metadata. Require an explicit open-source/self-hostability check before adoption.
- **Next step:** Use as an external automation option only for one approved, reversible workflow.
- **Caution:** Can create hidden background automation; keep manual until trusted.
- **Source:** known ecosystem tool

### Microsoft Conductor
- **Summary:** Agent coordination pattern for multi-agent workflows and durable orchestration.
- **Fit:** Useful once FPAI has a clean service map and knows which workflows deserve orchestration.
- **Sovereignty:** Hybrid — sovereignty posture unclear from available metadata. Require an explicit open-source/self-hostability check before adoption.
- **Next step:** Prototype one narrow orchestration loop after the service registry exists.
- **Caution:** Premature orchestration would amplify current repo sprawl.
- **Source:** approved scout target from docs/codex/README.md

### Graphiti / Temporal Knowledge Graph
- **Summary:** Episodic memory graph pattern for entities, events, and time-aware relationships.
- **Fit:** High long-term fit for FPOS memory, but only after current canonical surfaces are clean.
- **Sovereignty:** Hybrid — sovereignty posture unclear from available metadata. Require an explicit open-source/self-hostability check before adoption.
- **Next step:** Run a tiny proof on one source: qb questions or service registry history.
- **Caution:** Knowledge graphs become noise if source-of-truth boundaries are unclear.
- **Source:** known ecosystem pattern

### Open WebUI
- **Summary:** Local AI chat UI and model interaction surface.
- **Fit:** Not the current need; FPAI already has too many surfaces competing for attention.
- **Sovereignty:** Hybrid — sovereignty posture unclear from available metadata. Require an explicit open-source/self-hostability check before adoption.
- **Next step:** Ignore until there is a clear user group and one required model surface.
- **Caution:** Likely increases interface sprawl.
- **Source:** known ecosystem tool

### Dify / Flowise
- **Summary:** Visual LLM app builders for chat, retrieval, and tool workflows.
- **Fit:** Helpful for prototypes, less helpful for this repo's need for canonical clarity.
- **Sovereignty:** Hybrid — sovereignty posture unclear from available metadata. Require an explicit open-source/self-hostability check before adoption.
- **Next step:** Ignore for now; revisit only if a user-facing AI app needs rapid prototyping.
- **Caution:** Adds another admin surface before the current ones are mapped.
- **Source:** known ecosystem tool
