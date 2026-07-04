# Builder Academy · Module 1 — The $0 Build Loop

> **Build:** wire the smallest real autonomous loop that runs laptop-free at $0 marginal.
> **Principle it installs:** *cheapest sufficient carrier* — route always-on work to the flat-rate
> plan you already pay for, not a metered API.
> **Debrief question (the judgment you keep):** *"What did I just route — and what's the cheapest
> sufficient carrier next time?"*

_This is Module 1 because the whole system rests on this one choice. Get it wrong and every
autonomous loop meters you into the cost cap on day one. You won't believe that until you've built
the loop and watched it cost nothing — so build it._

---

## Prerequisites (the setup IS part of the lesson)
- **An always-on VPS.** Your laptop is not the substrate. If the loop dies when you close your
  laptop, it isn't a substrate — it's a script you babysit.
- **A flat-rate AI subscription** (Claude Max / ChatGPT Max) → its CLI: `claude -p` / `codex`.
  Flat-rate = you already paid; marginal calls are ~$0. This is the whole trick.
- **A git repo** the loop can branch + commit in.

## The build (the rep) — the smallest honest loop
A real loop has five organs. Build all five or you've built a toy:

1. **A queue** — where "what to build" lives (a file, or a DB row). One item = one job.
2. **A builder** — `codex` (or `claude -p`) reads the spec, writes the change **on a branch**.
3. **An independent reviewer** — `claude -p` reviews the diff and returns a verdict
   (`APPROVE` / `REQUEST_CHANGES`) as JSON. Use a *different lab* from the builder if you can —
   same-lab review is weaker (a bias both share won't be caught).
4. **A gate** — merge **only if** `APPROVE` **and** the change is reversible **and** nothing is
   BLOCKED. Never auto-merge to `main`.
5. **A clock** — a cron / systemd timer fires the loop every N minutes, on the VPS. Laptop-free.

## Guardrails — ship these WITH it, not "later" (this is Module 3 previewed, on purpose)
- **Kill-switch:** first line of every run checks for a `.disabled` file and exits if present.
- **Cost tally:** even a $0 loop logs its calls — so the day something silently starts metering,
  you *see* it instead of finding it on an invoice.
- **Reversible:** branch + review before merge; the loop can never touch `main` directly.
- **Small blast radius:** one change per run.

## The proof — graduation gate (demonstrate, don't explain)
You pass Module 1 when all four are true, shown live:
1. ☐ The loop runs on the VPS **with your laptop off**.
2. ☐ A cost check shows **$0 marginal metered spend** across a full day of runs.
3. ☐ You `touch .disabled` and the **next run halts**.
4. ☐ You feed it a deliberately bad build and the **reviewer BLOCKs it** before merge.

If you can only explain these but not show them, you haven't passed — that's the point (P1: attempt ≠ verified).

## The debrief — the cargo (write your answers; this is what actually transfers)
The build taught your hands the mechanics. These questions install the *allocation judgment* —
the part that survives when the tools change:
1. **What work did you just route to the flat-rate carrier — and what would it have cost metered?**
2. **What's ONE always-on thing in your current work still on a metered/expensive carrier that
   could move down the ladder?** (AI → paid-AI → 3rd-party → contractor → you.)
3. **When is metered API actually the *right* carrier?** (Hint: spiky, product-facing, per-customer
   — not always-on substrate.) Knowing *when to spend* is as much the skill as knowing when not to.

## Reference implementation (our live loop — read the real thing)
| Organ | Our system (server 162) |
|-------|-------------------------|
| Queue | `brain_index.decisions` (rows with `needs_build=true`) |
| Builder | `codex` CLI ($0, ChatGPT Max) |
| Reviewer | `tools/merge/ai_review.py` → `claude -p` (Claude Max, independent of the builder) |
| Gate | `tools/governance/constitution_check.py` + no-BLOCKED verdict + reversible |
| Clock | `fpai-build-loop.timer` (every 10 min) |
| Kill | `touch /opt/fpai-build/.disabled` |

Read those files. The debrief matters more than the code — but the code proves the debrief isn't fluff.

---
_Module 1 of the [[BUILDER_ACADEMY]]. Format: build → prove at the gate → debrief. Next module
installs guardrails/reversibility as its own rep. Graduation across modules is demonstrated, never
written._
