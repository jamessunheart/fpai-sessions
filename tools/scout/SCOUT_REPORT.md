# SCOUT REPORT

**Date:** 2026-06-05
**Focus:** clean up and focus the system
**Mode:** local deterministic seed scan; no network; no installs; no external spend.

## One Recommended Next Upgrade

**Service Registry / World Map** -> **build**

**Why:** Directly answers the current system problem: the substrate cannot optimize what it cannot see.
**Next step:** Generate a read-only service inventory from SERVICES/* metadata, then manually classify live/paused/archive.
**Caution:** Avoid broad automated edits; produce a report first, then route cleanup specs.

## Scored Intent

- **Intent:** Service Registry / World Map
- **Verdict:** build
- **Score:** 24
- **Route:** Codex spec before implementation; James approves consequential changes.
- **Definition of done:** Generate a read-only service inventory from SERVICES/* metadata, then manually classify live/paused/archive.

## Candidates

| Score | Candidate | Category | Verdict | Cost | Hits |
|---:|---|---|---|---:|---|
| 24 | Service Registry / World Map | system clarity | build | 1 | focus, system |
| 13 | Microsoft Conductor | agent orchestration | fork | 6 | clean |
| 12 | Obsidian Agent Skills | second brain | fork | 4 | - |
| 12 | LiteLLM / OpenRouter-style Model Router | model routing | API | 5 | - |
| 12 | n8n | workflow automation | API | 4 | - |
| 11 | Graphiti / Temporal Knowledge Graph | knowledge graph | fork | 7 | clean |
| 11 | Actual Budget | financial dashboard | API | 5 | system |
| 4 | Dify / Flowise | agent app builder | ignore | 5 | - |
| 4 | Open WebUI | AI interface | ignore | 4 | - |

## Candidate Notes

### Service Registry / World Map
- **Summary:** A canonical local registry of services, status, owner, URLs, deploy target, cost, and kill condition.
- **Fit:** Directly answers the current system problem: the substrate cannot optimize what it cannot see.
- **Next step:** Generate a read-only service inventory from SERVICES/* metadata, then manually classify live/paused/archive.
- **Caution:** Avoid broad automated edits; produce a report first, then route cleanup specs.
- **Source:** local need; existing SERVICES/INDEX.md is stale

### Microsoft Conductor
- **Summary:** Agent coordination pattern for multi-agent workflows and durable orchestration.
- **Fit:** Useful once FPAI has a clean service map and knows which workflows deserve orchestration.
- **Next step:** Prototype one narrow orchestration loop after the service registry exists.
- **Caution:** Premature orchestration would amplify current repo sprawl.
- **Source:** approved scout target from docs/codex/README.md

### Obsidian Agent Skills
- **Summary:** Skill-style workflows attached to an Obsidian vault and reused by agents.
- **Fit:** Strong fit for FPOS because James already uses the vault as visible memory.
- **Next step:** Fork the pattern into one repo-local skill for scout reports and proof logs.
- **Caution:** Do not let skill proliferation become another unindexed surface.
- **Source:** approved scout target from docs/codex/README.md

### LiteLLM / OpenRouter-style Model Router
- **Summary:** A thin routing layer for model choice, budgets, caps, and provider fallback.
- **Fit:** Good fit after cost meter is trustworthy; lets expensive calls route by task class.
- **Next step:** Add a read-only routing recommendation report before using any paid provider.
- **Caution:** Requires secrets and spend controls; never auto-wire providers from scout output.
- **Source:** known ecosystem pattern

### n8n
- **Summary:** Workflow automation engine with many connectors and human-readable flows.
- **Fit:** Useful for boring repeatable tasks after routing and permission boundaries are firm.
- **Next step:** Use as an external automation option only for one approved, reversible workflow.
- **Caution:** Can create hidden background automation; keep manual until trusted.
- **Source:** known ecosystem tool

### Graphiti / Temporal Knowledge Graph
- **Summary:** Episodic memory graph pattern for entities, events, and time-aware relationships.
- **Fit:** High long-term fit for FPOS memory, but only after current canonical surfaces are clean.
- **Next step:** Run a tiny proof on one source: qb questions or service registry history.
- **Caution:** Knowledge graphs become noise if source-of-truth boundaries are unclear.
- **Source:** known ecosystem pattern

### Actual Budget
- **Summary:** Local-first finance tracking and budgeting system.
- **Fit:** Potential fit for treasury visibility, but not the current clarity bottleneck.
- **Next step:** Evaluate after financial consolidation hub spec is active.
- **Caution:** Do not import sensitive financial data during scout phase.
- **Source:** known ecosystem tool

### Dify / Flowise
- **Summary:** Visual LLM app builders for chat, retrieval, and tool workflows.
- **Fit:** Helpful for prototypes, less helpful for this repo's need for canonical clarity.
- **Next step:** Ignore for now; revisit only if a user-facing AI app needs rapid prototyping.
- **Caution:** Adds another admin surface before the current ones are mapped.
- **Source:** known ecosystem tool

### Open WebUI
- **Summary:** Local AI chat UI and model interaction surface.
- **Fit:** Not the current need; FPAI already has too many surfaces competing for attention.
- **Next step:** Ignore until there is a clear user group and one required model surface.
- **Caution:** Likely increases interface sprawl.
- **Source:** known ecosystem tool
