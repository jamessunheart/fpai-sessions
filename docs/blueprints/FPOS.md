# Full Potential OS — System Blueprint
**Version:** 0.1 (seed — auto-sharpens after each build)
**Last updated:** 2026-06-16
**Status:** ~40% live spine, building outward

---

## What it is

A self-evolving personal AI platform. One Chat per user — with memory, routing, CORA rewards,
and capability extensions. Users enter through any channel. The system learns who they are,
routes them to the right next step, and proves they took it. Builds itself autonomously on
server 162. Laptop-free. $0 marginal cost via subscription CLIs.

---

## The 9 Functions

| # | Name | What it does | Status | Owner file |
|---|---|---|---|---|
| 1 | **Beacon** | Acquisition — QR/ad/link → attribution → content campaigns → conversion tracking | Building (d037-d038) | `curator/beacon/` |
| 2 | **Spark** | First-touch routing — 3 questions → understand situation/goal/energy → one specific path | Live | `tgbot.py` |
| 3 | **Ember** | Memory + context steward — holds the whole picture across sessions and surfaces | Live | `memory/` + `tgbot.py` |
| 4 | **Hermes** | Channel gateway — normalizes Telegram/web/SMS/WhatsApp into one pipeline | Building (d034) | `curator/hermes/` |
| 5 | **Council** | Architecture debate — 3 lenses propose ONE build, decision agent answers, loop builds | Live | `tools/council/debate.py` |
| 6 | **Forge** | Build loop — Codex builds + claude -p reviews + auto-merges + health checks + reverts | Live | `server_build_loop.sh` |
| 7 | **Steward** | Per-user agent — isolated namespace, profile, CORA balance, capability grants | Building (d039-d043) | `curator/agent/` |
| 8 | **Ledger** | Ops truth — records what ran, what failed, costs, correction signals | Live | `tools/build_loop/ops_log.py` |
| 9 | **Loop** | Self-evolution — captures corrections, builds preference pairs, learns | Building (d010-d023) | `tools/learn/` |

---

## How it assembles (the full flow)

```
User touches Beacon (QR / ad / link / referral)
  → Hermes normalizes the message (channel-agnostic)
    → Spark asks 3 questions (situation / goal / energy)
      → Ember loads context (who is this person, what do they need)
        → Route to ONE specific next step
          → User acts → Proof
            → Ledger records it
              → CORA awarded
                → Loop learns (correction signal / preference pair)
                  → Ember is smarter next session

Meanwhile (autonomous, on server 162):
  Council debates intents → proposes build
    → Decision agent auto-answers
      → Forge builds (Codex) + reviews (claude -p) + auto-merges
        → Blueprint updated → standard rises
          → Council proposes sharper next build
```

---

## Build loop (how the system improves itself)

1. Council runs every 5 min — reads intents + queue, debates with 3 lenses, proposes ONE build
2. Decision agent auto-answers if confident (d047: Intent Protocol Extractor handles rule extraction)
3. Build loop picks up `needs_build=true` decisions every 10 min (server 162, $0 via Codex)
4. claude -p reviews diff with `--effort high` — APPROVE or REQUEST_CHANGES
5. APPROVE → auto-merges to `feat/headless-build` → post-merge import check
6. If check fails → `git reset --hard pre-merge-SHA` (instant revert) → TG alert
7. Architecture doc (d048) regenerates → Blueprint (d050) updates → Smoke tests run (d049)
8. Morning digest (08:00 Athens) summarizes what built, what failed, what's next

---

## Quality standard (current)

- Every build ships with: tests, kill switch, rollback path, small blast radius
- No build touches prod without James approval
- Cost cap: $20/day hard ceiling (metered APIs only — subscriptions are $0)
- Auto-merge only on AI-APPROVE, never to main
- Smoke tests must pass within 6 hours of any merge

---

## Infrastructure

| Service | Host | What it runs |
|---|---|---|
| `sh-brain-tgbot` | 162 | Telegram bot (Spark + Ember for users, decision intercept for James) |
| `fpai-build-loop.timer` | 162 | Every 10 min — builds 5 decisions per run, 24/day cap |
| `fpai-council.timer` | 162 | Every 5 min — debate + propose |
| `fpai-morning-digest.timer` | 162 | 08:00 Athens — daily summary to TG |
| `sh-brain-postgres` | 162:25432 | brain_index DB — decisions, thread, corrections, user data |

**Kill switches:**
- Build loop: `touch /opt/fpai-build/.disabled`
- Council: `touch ~/.config/fpai/council/.disabled`
- Digest: `touch /opt/fpai-build/.digest_disabled`

---

## Key files

| File | Purpose |
|---|---|
| `server_build_loop.sh` | Autonomous build runner |
| `tools/merge/ai_review.py` | Independent code review (claude -p, --effort high) |
| `tools/council/debate.py` | Architecture debate (claude -p, --effort xhigh) |
| `core/STATE/NOW.md` | Founder priorities (SSOT — wins all conflicts) |
| `core/BUILD/REGISTRY.json` | What has been built |
| `tools/build_loop/ops_log.py` | Ops truth ledger |
| `tools/cost/track.py` | Cost tracking ($20/day cap) |
| `curator/decisions.py` | Decision queue CRUD + build triggers |
| `docs/blueprints/` | This directory — module contracts (you are here) |

---

## Module blueprints (individual)

Each module has its own blueprint in this directory:

| File | Module | Status |
|---|---|---|
| `forge.md` | Build loop | Pending (d050) |
| `council.md` | Debate + proposal | Pending (d050) |
| `ember.md` | Memory + context | Pending (d050) |
| `spark.md` | Routing + onboarding | Pending (d050) |
| `hermes.md` | Channel gateway | Pending (d050) |
| `steward.md` | Per-user agent | Pending (d050) |
| `beacon.md` | Growth engine | Pending (d050) |
| `cora.md` | Reward policy | Pending (d050) |
| `ledger.md` | Ops truth | Pending (d050) |
| `learning_loop.md` | Self-evolution | Pending (d050) |
| `health.md` | Health + smoke tests | Pending (d050) |

d050 builds all of these and wires auto-update so they sharpen after every merge.

---

## How blueprints improve

1. **After every build merge** — `update_blueprint_after_build()` runs, updates Current behavior + Improvement history
2. **After every correction** — James corrects something → correction captured → Known gaps updated
3. **After council review** — council proposes quality standard upgrade, James approves → standard rises
4. **Codex reads blueprints** — when building a module, receives its blueprint as context → builds to improve, not replace
5. **Council reads blueprints** — proposes against defined standard → sharper proposals
6. **Weekly spec checker** — confirms what was built actually matches what was specced

The standard only moves upward. Each cycle, the gap between current behavior and excellent narrows.

---

## How to share this with GPT

Paste this file (or `docs/ARCHITECTURE.md` when d048 builds) into GPT with:
> "This is the full architecture of my AI platform. Help me [visualize / improve / extend / explain] it."

Or paste the Mermaid diagram from ARCHITECTURE.md into GPT canvas to render visually.

---

## Gap log (what is NOT live yet)

- Per-user multi-tenancy (d039-d043: building)
- CORA policy (d035: building)
- Onboarding flow (d036: building)
- Beacon growth engine (d037-d038: building)
- Module blueprints (d050: queued)
- Living architecture doc (d048: queued)
- Smoke test suite (d049: queued)
- Tool mastery system (d046: queued)
- Intent Protocol Extractor (d047: building)
- Stripe billing (d043: building)
- Capability execution (d044: building)
