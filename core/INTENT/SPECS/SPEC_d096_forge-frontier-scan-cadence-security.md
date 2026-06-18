# SPEC d096 — Forge Frontier Scan: Cadence + Security Protocol

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## What

Two things:
1. **Scan cadence** — Forge runs external frontier scans on a schedule, not just pre-build
2. **Security protocol** — hard rules for what can touch external tools and what never leaves the system

## Why

Aggressive external scanning expands capability at near-zero cost. But sensitive data (corrections, contacts, treasury, personal DNA) must never reach external tools. The protocol makes both safe simultaneously.

---

## Security protocol: Two-layer boundary (PERMANENT RULE)

### Public layer — safe to send outward / to external tools
- Routing decisions (task type, complexity tier) — no content
- Anonymized signal patterns ("correction frequency by task type") — no raw corrections
- Journey stage names ("user at stage=awaken") — no identity
- Benchmark scores, latency metrics — no personal data
- Prompt templates (evolved by GEPA) — no personal context
- Architecture patterns, spec descriptions — no data

### Private layer — NEVER leaves the system, never reaches external tools
- `brain_index.corrections` — James's raw taste signals
- `brain_index.probe_pool` / `probe_sessions` — contact identities + conversations
- `brain_index.thread` — live conversation content
- `brain_index.decisions` — internal decision log
- `identity/` — Ember's personal DNA files
- `core/STATE/PERSONAL_DNA.md` — James-specific layer
- Treasury data, financial records
- Any credential or API key

### Integration rule for adopted external tools
External tools (Dittofeed, GEPA, vLLM router) receive:
- **Triggers** (anonymized events): "segment:stage_awaken entered" — not who
- **Patterns** (aggregated): "correction_rate=0.3" — not the corrections themselves
- **Config** (routing rules): "route code tasks to T1" — not the task content
- **Never**: raw personal data, contact PII, correction content, conversation history

---

## Scan cadence (three tiers)

### Tier 1 — Per-build scout (d094, already queued)
- Fires: before every codex build
- Scope: internal inventory + external library/framework check for the specific spec
- Runtime: ~30s, $0 via claude -p
- Output: appended to spec before codex runs

### Tier 2 — Daily lightweight scan (NEW — this spec)
- Fires: 07:00 Athens daily (before morning digest)
- Scope: HuggingFace new models, GitHub trending AI repos, X/Twitter AI announcements
- Runtime: ~3min, $0 via claude -p
- Output: findings appended to `core/STATE/FRONTIER_LOG.md`
- Surfaces to morning digest only if QUANTUM_LEAP score ≥ 7/10

### Tier 3 — Weekly deep scan (NEW — this spec)
- Fires: Monday 06:00 Athens
- Scope: full frontier scan across ALL active build areas (same as today's Forge session)
- Runtime: ~15min, $0 via claude -p
- Output: `core/STATE/FRONTIER_WEEKLY_{date}.md` + surfaced to TG if top finding scores ≥ 8/10
- Includes: arXiv recent papers, ProductHunt AI launches, major GitHub releases, framework updates

### Scan focus areas (updated from active specs)
- Learning / self-improvement (GEPA, fine-tune, prompt evolution)
- Multi-channel messaging (WhatsApp, email, voice)
- Routing / intelligence ladder
- Contact discovery + enrichment
- Becoming-engine / journey orchestration
- Local model inference (Ollama alternatives, quantization)
- Council / multi-agent frameworks
- Cell-split / instance templating

---

## Deliverables

### `tools/forge/daily_scan.py`
- Runs claude -p with web search against active build areas
- Scores each finding: relevance (1-10), adoption cost (low/med/high), quantum_leap (bool)
- Appends to `core/STATE/FRONTIER_LOG.md`
- Triggers TG notification if quantum_leap=true

### `tools/forge/weekly_scan.py`
- Full Forge invocation across all active areas
- Produces structured report: QUANTUM_LEAP / ADOPT / WATCH sections
- Compares against last week's report — surfaces NEW findings only
- Commits report to repo (human-readable history of what the system learned about itself)

### `core/STATE/FRONTIER_LOG.md`
- Rolling log of external findings
- Format: `[date] [tier] [area] [tool/project] [score] [action: ADOPT/WATCH/SKIP]`
- Council reviews weekly and promotes ADOPT items to specs

### systemd timers
- `fpai-forge-daily.timer` — 07:00 Athens, daily_scan.py
- `fpai-forge-weekly.timer` — Monday 06:00 Athens, weekly_scan.py

### Security gate (runs before every scan output is written)
- `tools/forge/security_gate.py`
- Scans scan output for: email addresses, phone numbers, correction content, contact names
- If found: strips and logs warning
- Ensures no private layer data leaks into FRONTIER_LOG or scan reports

---

## Gates
- `FORGE_SCAN_ENABLED=1` env flag
- Daily scan: max 3min runtime, auto-abort if exceeded
- Weekly scan: max 20min runtime
- All scans run on claude -p ($0 marginal)
- Security gate: blocks any scan output containing private layer patterns

## Proof
- 7 consecutive daily scans complete without private data in output
- Weekly scan surfaces at least 1 ADOPT or WATCH item
- Security gate blocks a test injection of a contact email address
