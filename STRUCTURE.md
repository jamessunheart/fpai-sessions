# FPAI_COCKPIT — STRUCTURE

**Cockpit map.** Resolves "current priority" → in-scope artifacts. Derived from `core/STATE/NOW.md`.

- For the **why**: [`core/INTENT/COHERENT_CHAMPIONS_MANIFESTO.md`](./core/INTENT/COHERENT_CHAMPIONS_MANIFESTO.md)
- For the **now**: [`core/STATE/NOW.md`](./core/STATE/NOW.md) — SSOT
- For the **how (engineering)**: [`core/INTENT/PRINCIPLES.md`](./core/INTENT/PRINCIPLES.md)
- For the **how (cooperation)**: [`core/INTENT/FORMING_AGREEMENTS.md`](./core/INTENT/FORMING_AGREEMENTS.md)

---

## Mission Layer — `core/INTENT/`

The supreme intent. Two layers; Layer 1 governs Layer 2.

| File | What |
|---|---|
| [`core/INTENT/README.md`](./core/INTENT/README.md) | Layer clarification (Mission vs Engineering Substrate) |
| [`core/INTENT/COHERENT_CHAMPIONS_MANIFESTO.md`](./core/INTENT/COHERENT_CHAMPIONS_MANIFESTO.md) | Manifesto v1.0 — founding document of WPO / Zen Village |
| [`core/INTENT/WORLD_PEACE_AGREEMENT.md`](./core/INTENT/WORLD_PEACE_AGREEMENT.md) | Canonical template for forming Peace Agreements |
| [`core/INTENT/FORMING_AGREEMENTS.md`](./core/INTENT/FORMING_AGREEMENTS.md) | Protocol for instantiating specific Agreements |
| [`core/INTENT/AGREEMENTS/`](./core/INTENT/AGREEMENTS/) | Specific formed Agreements (one file per instance) |
| `core/INTENT/IDENTITY.md`, `PURPOSE.md`, `PRINCIPLES.md` | Layer 2 — engineering substrate (older, narrower scope) |

**Naming**: World Peace Party = World Peace Organization = World Peace Headquarters = Zen Village.
**Founder**: James Sunheart.
**Mission**: paradise on Earth through cooperation.

---

## Living State — `core/STATE/`

| File | What |
|---|---|
| [`core/STATE/NOW.md`](./core/STATE/NOW.md) | **SSOT for current priority and what's live.** Read first. |
| `core/STATE/HEALTH.md` | System health snapshot |
| `core/STATE/ASSEMBLY_LINE.md` | Active builds |
| `core/STATE/PROGRESS.md` | Progress tracking |
| `core/STATE/INBOX.json`, `TREASURY.json` | Machine-readable state |

---

## Current Priority Surface (per NOW.md, 2026-05-07)

### Priority 1 — REVENUE ACTIVATION (FPI v5.6.0 live)

| Artifact | Path | Server | Port | Status |
|---|---|---|---|---|
| FP Index | `SERVICES/fp-index/` | Primary `198.54.123.234` | 8550 | LIVE |
| Credits Gateway | (server-side) | Primary | 8765 | LIVE — Stripe configured |
| WhaleTrack Magnet | `whaletrack-magnetic-trader/` | Primary | 8600 | LIVE — paper trading |
| Public site | `https://fullpotential.ai/` | Primary | 80 (nginx) | LIVE |
| Intelligence feed | `/intelligence` (427+ entries) | Primary | — | LIVE |
| AI Brain | (consciousness/intel hub) | Secondary `162.0.208.88` | 8101 | LIVE |
| Ollama | 6 models loaded | Secondary | 11434 | LIVE |

**Honest scorecard from NOW.md** (March 2026): Constitutional architecture 85%, Economic design 80%, Frontier scanning 85%, Pipeline 75%, Content/share 75%, **Revenue 5%** (no human purchase yet).

### Priority 2 — Manifesto adoption + Agreement formation (2026-05-07)

In-scope: see Mission Layer above. The manifesto retroactively names what's already built — see operational alignment table at the bottom of `COHERENT_CHAMPIONS_MANIFESTO.md`.

### World Peace Weekend (May 2–3, 2026)

| Artifact | Path |
|---|---|
| Public landing | `https://zenvillage.live/peace` |
| Repo source | (search for `peace` directory in recent commits — see `git log --grep=peace`) |
| QR codes | committed `f288b5c3` |

### Backlog — Built, Deploy Pending

| Service | Path | Port | Note |
|---|---|---|---|
| TRUST Index | `SERVICES/trust-index/` | 8560 | Membership primitive of the Agreement |
| Contribution Tracker | `SERVICES/contribution-tracker/` | 8570 | TRUST token issuance |
| Needs Allocation | `SERVICES/needs-allocation/` | 8565 | Needs distribution engine |
| Commons Stack | `SERVICES/commons-stack/docker-compose.yml` | — | Docker stack ready |
| Strategic Intelligence M022 | `SERVICES/strategic-intelligence/` (v2.0) | 8500 | Built; deploy pending |

---

## Two-Server Architecture (Quick Reference)

```
PRIMARY (198.54.123.234)              SECONDARY (162.0.208.88)
─────────────────────────              ────────────────────────
8550  FP Index v5.6.0     LIVE         8101  AI Brain           LIVE
8765  Credits Gateway     LIVE         8130  Consciousness      ACTIVE
8600  WhaleTrack          LIVE         11434 Ollama (6 models)  LIVE
8125  Data Service        LIVE         Multiple intelligence services
8120  Nerve Center        LIVE
8500  Strategic Intel     LIVE
8300  God Mode            MONITORING
80    Nginx               ROUTING
```

```python
# API routing constants (from NOW.md)
AI_BRAIN_URL = "http://162.0.208.88:8101"     # Secondary
FP_INDEX_URL = "http://198.54.123.234:8550"   # Primary — Constitutional Economy
CREDITS_URL  = "http://198.54.123.234:8765"   # Primary — Credits Gateway
DATA_SERVICE = "http://198.54.123.234:8125"   # Primary
TRADING_URL  = "http://198.54.123.234:8600"   # Primary — WhaleTrack Magnet
```

---

## Brain / Memory Surface

| Brain | URL / Path | Use |
|---|---|---|
| Sunheart Brain | `brain.sunheart.com` (MCP) | Cross-tool memory; Cursor + CLI + Claude all read it |
| Zen Village Brain | `brain.zenvillagecr.com` (MCP) | Project-scoped (Zen Village retreat) |
| Local memory | `~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/MEMORY.md` | Auto-memory across sessions |

**Known issue (2026-05-07)**: both brain MCP endpoints failing on auth. Sunheart-brain token lacks `ingest` scope (`personal`+`public` only). Zen Village brain returning 400 from gotrue (stale Supabase creds). Fix per memory: `sync /etc/sh-brain/mcp-http.env from /root/sh-brain-secrets/brain.env` on `162.0.208.88`.

---

## Out of Scope (cruft to ignore unless explicitly cleaning)

These do not advance the current priority. **Default answer to "should we touch this": no.**

- **80+ capitalized `.md` files at repo root** (`BREAKTHROUGH_*`, `AUTONOMOUS_*`, `GOD_MODE_*`, `START_HERE_*`, `URGENT_HIRE_*`, `MISSION_CONTROL_*`, etc.) — mostly stale status docs from earlier eras
- **Most of `SERVICES/` (178 entries)** — most paused. Deploy-relevant subset is the table above.
- **`_staged_repos/`, `_status/`, `.archive/`** — historical
- **Root-level scripts** (`cli_dashboard.py`, `god_mode_server.py`, `treasury_monitor.py`, etc.) — unclear authority; check with founder before running
- **`metaclaw` / `openclaw-gateway`** — disabled 2026-04-30 (per memory)

---

## How To Use This Map

1. **Cold start?** Manifesto → NOW.md → this file → the artifact you need.
2. **Working on current priority?** Stay in the "Current Priority Surface" rows.
3. **Adding something new?** Check NOW.md first. If not there, ask whether it belongs at all before creating files. Bias toward not.
4. **Found cruft?** Note it; do not delete without explicit permission. The `mcp__ccd_session__spawn_task` tool is good for filing cruft cleanups as separate sessions.

---

## Update Discipline

**This map is derived from `core/STATE/NOW.md` as of 2026-05-07.**

When NOW.md changes substantively (new priority, new live service, new shutdown), this file may go stale. Treat NOW.md as authoritative when they disagree.

A future `tools/gen_cockpit_map.py` could regenerate this file from NOW.md automatically. Not built yet.
