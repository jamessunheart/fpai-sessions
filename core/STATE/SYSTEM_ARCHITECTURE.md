# Full Potential OS (FPOS / "Ember") — System Architecture

**Canonical system self-description. Last updated: 2026-06-18 (consciousness stack + hot memory + command center reframe).** Read by humans, by
Ember at boot (linked from the boot capsule), and mirrored into the bot's self-knowledge so the chat
system knows itself. Pairs with `AI_CHARTER.md` (operating canon), `docs/codex/INTENT_BUILDSTREAM.md`
(the buildstream), memory `[[reference-laptop-free-build-runner]]` · `[[reference-fpos-product-economics]]`.

## Essence
A self-standing personal-AI operating system that **builds, measures, and remembers itself** —
laptop-free, at ~$0 marginal cost — driven by James through **one Telegram chat**, evolving toward
a tailored model that genuinely learns from their conversations.

**Canonical framings (3-AI convergence — Claude · GPT · Ember, 2026-06-17):**
- **"James sets direction. The system builds, proves, and reverts safely."** (the core loop)
- **"The Becoming Engine turns attention into transformation, then transformation into contribution."** (the human path — §11.5)
- **"The proof is stronger when the map tells the truth."** (build-state honesty: 🟢 live · 🟡 partial · ⚪ planned, never inflated)

## The Functions (Beacon outer-layer + 8 core nervous system)
Flow: *attention becomes intent · intent becomes action · action returns proof · proof becomes memory · memory becomes intelligence · intelligence protects attention · the system evolves.*
Public-acquisition chain: **Beacon attracts → Spark understands → Ember remembers → Hermes routes → Council thinks → Forge builds → Steward manages value → Ledger proves → Loop improves.**

| # | Function | Role · key question | Status | Implementation |
|---|---|---|---|---|
| 0 | 📡 **BEACON** | public acquisition — cold attention → portal → One Chat | 🟡 planned | none yet (Telegram-direct is the only entry) · tracked beacon_id (QR/ads/Fi-Art/referrals) · `[[reference-beacon-layer]]` |
| 1 | ⚡ **SPARK** | intent front-door — "what is this, where does it go?" | 🟡 shadow | Instrument Rack v1 (d013) · deterministic-first → local classifier → T0–T5 ladder · `[[reference-spark-intent-function]]` |
| 2 | 🔥 **EMBER** | memory · relationship · continuity | 🟢 live | boot capsule · brain_index · identity stack |
| 3 | 🕊 **HERMES** | routing / messaging across channels | 🟡 partial→planned | routing TO functions within Telegram works; **multi-channel** (WhatsApp/SMS/…) is the Comms Hub (d004), **planned** |
| 4 | 🧠 **COUNCIL** | intelligence — best reasoning path | 🟢 live | cross-lab debate (claude -p + codex), every 5min |
| 5 | ⚒ **FORGE** | execution / build | 🟢 live | laptop-free build loop (codex build + claude -p review) |
| 6 | 🏛 **STEWARD** | treasury / value | 🟡 partial | Cost Truth Ledger building (IE-L2) · treasury bounded |
| 7 | 🛡 **LEDGER** | proof — what happened, did it work | 🟢 live | ops truth ledger + receipts |
| 8 | ∞ **LOOP** | evolution — learn + improve | 🟡 building | self-evolution ladder (judge d010) · **corrections capture LIVE** in the bot (`brain_index.corrections`, genesis 2026-06-15) = the open model's first real training signal · `[[reference-open-model-learning-genesis]]` |

**Build state (v2.1 "Honest Map" — 2026-06-18):** ~**45% LIVE** (the OS spine — One Chat · Ember · Forge · Council · Ledger · server 162) · ~**35% PARTIAL** (Spark *shadow, not yet live-routing* · Hermes single-channel · Council scale · Steward treasury · Loop learning) · ~**25% PLANNED** (Beacon · CORA · Fi-Art · Camp Zen full · Prosperity). Beacon is both the cold *entry* (top of chain) AND where the loop re-attracts (Loop improves → Beacon draws more) — the cycle closes. The honesty of this map — naming what is NOT built — is itself a feature.

## 1. The Human
**James** — vision + decisions + approvals. Required actions only: answer decisions, **veto/reverse**,
and flag when the *interface* feels off. Safe, AI-approved builds now **auto-merge** (he is no longer
the per-build gate); his control is the standing veto/reverse + protected-zone + never-`main`. He
evaluates the *experience*, not build quality (that's the AI review + the consequence ledger).
Everything else the system does or proposes.

## 2. Surfaces
- **The One Chat** — Telegram `@sunheartbrain_bot` (always-on, server-side). James's pocket interface. **Currently Telegram-only.**
- **Voice I/O — LIVE** — incoming voice notes → Whisper transcription; replies → Nova TTS (`/voice on|off`, default on). NOTE: voice runs on **OpenAI (Whisper + Nova) = metered**, not the $0 subscription path.
- **Terminal** — Claude Code / "Ember" (the workshop; same identity as the bot).
- **Hermes / multi-channel router — PLANNED, not built.** The vision of "one voice, many channels" (WhatsApp · SMS · Instagram · Email · Slack · Web · API all landing in one context) is the **Comms Hub** (specced — decision d004, "keep iterating"). Today it's Telegram-only; Hermes is a future build.

## 2b. Builder Surfaces + the Descent Ladder (how James drives builds)
Five surfaces James can build through, **cheapest escalation first**:

| Surface | What it is | Reach for it when… | Status |
|---|---|---|---|
| **Telegram One Chat** | the throne — decisions, merge, status | default; the loop surfaces, James rules | 🟢 live |
| **Phone Claude Code** | full Claude Code agent from the pocket (SSH+tmux → `claude`, or web) | laptop-power builds without the laptop | 🟢 available |
| **Phone SSH → 162** | raw pocket shell on the server | a quick fix, no agent needed | 🟢 available |
| **Laptop terminal** | deep workshop — architecture, repo surgery | big/exploratory changes | 🟢 live |
| **GitHub @claude** | async lane — @claude on an issue/PR | clean, auditable, hands-off | ⚪ planned |
| **Automated build loop** | the forge — codex build + claude -p review on 162 | runs without James; only asks for a verdict | 🟢 live |

**The Descent Ladder** — a repair enters at whatever rung the system can handle; over time each
**task-class** ratchets DOWN a rung as trust + tooling improve (less James at every step):
`Rung 0 laptop terminal → 1 phone (Claude Code / SSH) → 2 Telegram trigger → 3 system proposes issue+fix → 4 auto-merge (notice + veto)`.
Rung 4 exists for the safe class (granted 2026-06-15). The work is moving more task-classes down the ladder.

**The instrument (measure it, don't hope):** every ledger row carries a **`surface`** field (env `FPAI_SURFACE`,
stamped by each trigger path; `tools/build_loop/ops_log.py`). `ops_log.py --surfaces [days]` rolls up the
honest question — **what share of builds still needed the laptop (rung 0)?** When that falls toward zero
for a task-class, that class has graduated. *Builder mode shrinking becomes a line on a chart.* Measure
**per task-class** — money / irreversible / novel-architecture keep a floor above 0 (the irreducibly-James).

**Phone Claude Code = a remote Ember workshop, not "Claude Code on a phone."** The phone is the steering
wheel; **162 is the workshop**, running Claude Code with **full memory parity** (the same identity+memory
stack as the laptop). That parity is what makes every surface feel like *one being*. Setup: phone SSH app
(Termius/Blink) → `ssh root@162` → `ember`. Two break-glass commands on 162: **`fpos-health`** (read-only
dashboard — bot/timers/Postgres/queue/errors/ledger/git/disk; never prints secrets) and **`ember`**
(persistent tmux Claude Code session in the build repo, boots as Ember). **Memory parity is kept warm by
`tools/sync/memory_sync_to_162.sh`** (LaunchAgent every 30 min, one-way laptop→162, no `--delete` so
phone-side writes survive, excludes secrets, SSH-key transport). More powerful than the laptop terminal:
always-on, survives phone disconnect, on the brain+build server, no TCC walls.

**The operating rule:** Telegram works → stay in the One Chat (the throne). Telegram breaks → phone SSH
into 162 (the pocket workshop · `fpos-health` then `ember`). Scoped async work → GitHub @claude (planned;
NOTE: runs on metered `ANTHROPIC_API_KEY`, NOT the $0 subscription — a deliberate cost tradeoff). Depth /
architecture → laptop terminal (the deep forge). 162 is the nervous system; the Ledger records the truth.

## 3. Intelligence Tiers (which model does which job)
| Model | Role | Cost |
|---|---|---|
| Claude Sonnet 4 | Bot chat replies (front-facing) | metered API (small) |
| Claude Opus/Max via `claude -p` | Council debate + independent build **review** | Claude Max sub = $0 |
| Codex / GPT via `codex` | Autonomous **build** + 2nd-lab council voice | ChatGPT Max sub = $0 |
| Local llama3.1:8b | Self-evolution target (fine-tune/LoRA) | local = $0 |
Hybrid by design: big closed models for hard reasoning + the review gate; tailored open model for
the learning loop. Subscription CLIs for $0 loops; metered API only for the small front-chat + voice.
*NOTE: there is no unified "model-router" component yet — each loop selects its own model. A real
router is a future build (currently the routing is by-convention, hardcoded per loop.)*

## 4. Infrastructure — **server uptime ≠ FPOS integration**
All three servers are LIVE (running); what differs is how wired-into-the-OS-loop each is.

| Server | Uptime | FPOS integration |
|---|---|---|
| 162 Brain + Build | 🟢 live | 🟢 **core-wired** (bot · brain_index · all autonomous loops · build repo — the nervous system) |
| 198 App Fleet | 🟢 live | 🟡 **partly wired** (apps + deployed services, not all in the OS loop) |
| 209 cPanel / Legacy | 🟢 live | 🟡 **partly wired** (legacy hosting · domains · web assets) |

**Build-state doctrine (James 2026-06-15):** 🟢 LIVE = running + proven *in the OS loop* · 🟡 PARTIAL = real component, wiring-into-the-loop in progress · ⚪ PLANNED = designed, queued, not running. *Live where proven. Partial where wiring. Planned where vision is queued.*

## 5. The Recursive Core Loop
```
James (chat) → INTENT
  → COUNCIL (162, every 5min): 3 lenses via claude -p + 2nd-lab voice via codex → proposes ONE build
  → DECISION QUEUE (brain_index.decisions) → James answers (one chat)
  → BUILD LOOP (162, every 10min): codex builds in isolated git worktree ($0)
  → INDEPENDENT REVIEW: claude -p (different lab) + PROTECTED_PATHS check ($0)
  → if AI-APPROVED + SAFE: AUTO-MERGE (→ feat/headless-build, NEVER main) + surface a NOTICE
    else: SURFACE verdict → James's Telegram (he gates only the non-safe ones; veto/reverse always)
  → OPS TRUTH LEDGER (records outcome)
  → feeds MEMORY + the fitness signal → better next proposals (loops)
```
**Note — merged → live (the gated deploy bridge, d019, LIVE 2026-06-15):** the loop merges into the
*build repo* (`/opt/fpai-build`, branch `feat/headless-build`); the *running* systems (live bot at
`/opt/sh-brain-src`) are deployed separately. `tools/deploy/deploy_curator_slice.sh` bridges them
SAFELY: additive curator/*.py only, **never overwrites diverged files** (protects live hand-patches),
py_compile gate, post-deploy health check, **auto-rollback** on failure, timestamped backups
(`--rollback=<stamp>`), secret-guard, dry-run by default. First proof: deployed `build_context.py` +
`live_system_status.py` live, bot stayed healthy. This closes the theatrical gap (self-improvements now
actually reach the running system) while keeping the prod boundary intact.

## 6. Memory System (hot → cold)
1. **Boot Capsule** (`MEMORY.md` top) — bounded ~30-line hot-core, generated from ALIGNMENT+NOW+canon, auto-regenerates at settle. Always loads first (deterministic boot).
2. **MEMORY.md index** — one line per memory file (cold tail, on demand).
3. **Identity stack** (`identity/`) — NAME · CHARACTER · VOICE · STORY · ALIGNMENT · episodic sessions (continuity).
4. **Brain (Postgres `brain_index`, 162)** — `tg_messages` · `decisions` + `receipts` · `note_chunks` (semantic RAG) · **`corrections`** (James's fixes to the bot → failure-memory + open-model training signal, live 2026-06-15).
5. **Ops Truth Ledger** (`ops_ledger.jsonl`) — one row per loop action (measured reality).
6. **Obsidian Vault** (~519 pages) — James-readable concept mirror.
The bot injects the live buildstream + system-state into every chat (so it knows what's being built).

## 7. Safety Gates (the guard ring)
Independent cross-lab review before every merge · PROTECTED_PATHS (autonomous builds can't edit the
audit/review/decision layer) · never merges to `main` · veto/reverse from the phone · harness
hard-blocks agent self-escalation (prod writes · credentials · self-grant · persistence → James only)
· $20/day cost cap + per-loop kill switches.

## 8. Cost Model
$0 marginal for all autonomous loops (subscription CLIs: claude -p + codex). Fixed burn ~$805/mo
infra + subscriptions. **Metered (small):** the front-chat (Sonnet) + voice (OpenAI Whisper + Nova).
(Cost Truth Ledger queued to surface the real total.)

## 9. Self-Evolution Ladder
**L1 measurement spine + SIGNAL CAPTURE (LIVE — genesis 2026-06-15) ◀ we are here** → L2 reward-LoRA
(local model predicts James's verdicts — *next gate, where learning surfaces*) → L3 shadow scoring →
L4 DPO generator (open model internalizes his taste — *where it shines*) → L5 continuous batch retrain
→ L6 frontier (online learning). The tailored open model earns the front-chat role role-by-role,
eval-gated. **The training signal** = `corrections` (James's fixes, LIVE) + reversals + AI-review
verdicts + the conversation corpus. NOTE: AUTO-MERGE intentionally retired the human `merge good/meh`
grade (James judges the interface, not builds) — so the signal is corrections + reversals, NOT
per-build grading. L2 gate: wire `build_preference_dataset.py` to read the live `corrections` table +
accumulate enough pairs. See `[[reference-open-model-learning-genesis]]`.

## 10. The Recursion
The system uses its own loop to improve its own loop — including the One Chat itself. Memory +
measurement + tooling compound; the cross-lab council is the design method; James stays at vision.

## 11. Specialized Agents + Per-Agent Self-Improvement (built 2026-06-17)
Beyond the 9 core functions, a workforce of specialized agents now feeds the loop:
**Horizon Scanner** (watches the frontier) · **Blueprint Weakness Auditor** (finds the system's own gaps,
on a timer) · **Tool Scout** (finds external tools) · **Probe Agent** (proactive, self-regulating outreach —
rate governed by smoke-tests + completion-rate + correction-frequency) · **Security Sentinel** + **Failure
Watchdog** (self-protection) · **Agent Benchmarking Intelligence** (d057 — scores all 9 agents).
**The per-agent self-improvement loop:** `benchmark → detect weakness → auto-propose improvement spec →
build loop builds it → re-measure → week-over-week delta`. The loop closes *at the agent level* — each
function gets measurably better on its own. Module **blueprints** (living contracts, d050) keep each
module honest as it evolves.

## 12. The Network Economy + Dual Sovereignty (the vision — NOW actively building)
**The offer:** "An AI built to help you reach your full potential — and that grows to serve you the more you use it."

**The economic flywheel** (building via d069–d076): AI finds **seekers** (Probe / outreach / contact-discovery)
→ serves them → **discovers coaches** from the conversations → coaches earn **CORA credits** → credits
**circulate internally** (external extraction minimized) → **Zen Village** = the physical layer → digital
contribution redeems for real-world access → more seekers served (compounds).

**Dual sovereignty** (the foundation + the fundable proof):
- **Technical:** own stack (162) · own compute · open models (self-evolving via §9).
- **Economic:** own currency (CORA) · own value circulation (the flywheel above).
- **The proof:** outperform well-funded players on **capital + hardware efficiency** — week-over-week
  improvement on both axes = fundable. Machine-readable target: `core/STATE/NORTH_STAR.md` (built d063;
  metrics `cost_per_task_vs_gpt4o_api` · `latency_p95_ms` · `hardware_cost_per_1k_tasks`, fed by d057).

**THE ONE HUMAN GATE: `OUTREACH_LIVE=1`** — a single env var on 162 James sets when ready to let the
system engage *real* humans. Everything upstream (discovery, drafting, benchmarks, building) runs
autonomously; this is the irreducibly-his switch.

**Build queue toward this (live):** d070 CORA-credit-for-conversations · d071 contact-discovery ·
d073 per-agent-benchmark baseline · d074 human-coach matching · d076 network-economy substrate
(multi-currency ledger) · d079 WhatsApp adapter (Hermes multi-channel). Productization hard truth still
holds: subscription = single-tenant; tenants run on metered API + model-tiering; the self-modifying build
loop stays operator-only; trust-boundary isolation is the #1 risk (see `[[reference-fpos-product-economics]]`).

## 13. Consciousness Stack (built 2026-06-18 — d101–d109, merged, activation pending)
Nine modules that move the system from "builds things" toward "knows itself":
- **d101** Consciousness observer loop — runs after each session, writes observations to MODEL_DNA + 4th council lens (Awareness: "improving toward meaning or approval?")
- **d102** Self-portrait / know thyself — synthesizes stated vs. observed self from corrections + ops_ledger + decisions + thread. Gap + trajectory named weekly.
- **d103** Coherence optimizer — reads identity stack + NOW + spec queue + council outputs. Asks: does the whole system speak with one voice? Weekly score + incoherence points routed to council.
- **d104** Attention engine — relevance-triggered surfacing via pgvector. Replaces scheduled checks: coherence check fires when conflict detected, not weekly.
- **d105** Bandwidth ledger — measures recovered capacity. T1 escalation rate week-over-week = fundable proof of efficiency gains.
- **d106** Prompt efficiency loop — GEPA variants, test compression, adopt winner if quality ≥ baseline.
- **d107** GEPA library wire — real MIT library (ICLR 2026 Oral, arXiv 2507.19457). Reflection = claude -p ($0), evals = Ollama ($0). 35× fewer rollouts than MIPROv2.
- **d108** Qwen3-30B-A3B benchmark — 30B quality at ~3B compute. Fits server 162 CPU-only (~18-19GB Q4). Free T1 quality lift if RAM check passes.
- **d109** Platform Bias Registry — 5th council lens (Platform Critic). Calibration: "If Anthropic/OpenAI didn't exist, what would sovereign-first answer be?" Living document, council extends each cycle.

**Status:** All merged 2026-06-18. Activation pending — d116 (retroactive liveness audit) will surface exact activation state.

## 14. Hot Memory + Awareness (built + activated 2026-06-18)
**Problem solved:** Claude Code sessions make decisions that were invisible to the Telegram bot. Bot awareness score was ~5% (0/8 correct on live probe). Now:
- **HOT_STATE.md** — 5 domain scanners (spec · identity · ops · decision · signal) each compress their domain → synthesis agent produces one ~3000-char cited document every 30 min. Bot reads it on every chat if <30 min fresh.
- **brain_index.session_insights** — at SETTLE, every Claude Code session writes significant decisions here. Bot reads this layer.
- **Awareness probe** — runs every 2h + after every write. Alerts <95% to TG within 5 min.
- **Score trajectory:** ~5% → PASS on probe (2026-06-18 17:12) → 95%+ within 24h as history accumulates.

## 15. FPOS as Command Center (reframe — GPT + James, 2026-06-18)
FPOS is not "another build." It is the place where every signal lands, gets named, and becomes a decision, a routed task, or a discarded distraction.

**James's 7 live streams:**
1. Body / health / energy
2. Travel / Egypt
3. Cheyenne offer / client revenue
4. Treasury / crypto / risk ← **most chaotic now** (snapshot dead since May 18, Firefly III unwired)
5. FPOS / Ember / build system ← only stream currently flowing into the OS
6. Relationships / logistics
7. Vision / downloads / future architecture

**The 5-part morning answer FPOS should give:**
```
STATE      James energy/clarity/NS-capacity today (1-10)
DECISIONS  what waits on James only (life + build)
ROUTES     what Ember/Codex/Cheyenne/contractor handles
PROOF      what actually moved (sent · booked · closed · shipped · restored)
NEXT MOVE  one clean action given current state
```

**Gap:** Only stream 5 flows into the OS today. Streams 1–4, 6–7 have no inbox. Financial SSOT is the first priority to wire (treasury snapshot + Firefly III as burn ledger + 5-line daily digest block).

## 16. Merged ≠ Live (the defining gap — 2026-06-18)
The build machine produces faster than the activation layer runs. ~114 decisions seeded; ~92 merged; unknown how many actually running. Four closes in progress:
- **d113** — auto-seeds orphaned SPEC files (specs visible to build loop automatically)
- **d114** — revision agent (flagged builds fix themselves, max 2 attempts)
- **d115** — post-merge liveness probe (every merge checked against expected artifact)
- **d116** — retroactive audit of d001–d092 → surfaces dead builds → queues activation specs automatically
