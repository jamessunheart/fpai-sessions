# NEXT SESSION — start here  (handoff 2026-06-11, before James's restart)

Read this first. It's the single source of truth for what's done and what's left.
Full audit trail: `core/BUILD/PROOF_LOG.md`. Buildstream context below.

---

## ⛳ THE ONE THING (do/ask first)

**The Watchfire deploy is built and waiting on James to run it.** A reversible one-paste script
ships the position-protection reconciler to the live whaletrack host, fixes the broken Python env
(the real root cause stops never fired), protects the 2 unprotected live shorts, and arms a 2-min
timer. James must run it himself — an AI **cannot** self-grant prod/codex permissions (hard safety
boundary; this is correct, "THE THRONE").

```
bash ~/FPAI_Cockpit/tools/build_loop/deploy_reconciler.sh        # full deploy
bash ~/FPAI_Cockpit/tools/build_loop/deploy_reconciler.sh --dry  # inventory only, no orders
bash ~/FPAI_Cockpit/tools/build_loop/deploy_reconciler.sh --revert
```

**Next session:** ask James if he ran it. If yes → verify resting stops landed (below). If no →
re-surface it as the red focus.

### Verify deploy worked (read-only, safe to run)
```
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@198.54.123.234 \
 'python3 - <<PY
import json,urllib.request
a="0xefbfead1189f32bc1000d3740445d0227286b77b"
def i(t):
 r=urllib.request.Request("https://api.hyperliquid.xyz/info",data=json.dumps({"type":t,"user":a}).encode(),headers={"Content-Type":"application/json"});import urllib.request as u;return json.load(u.urlopen(r,timeout=10))
print("triggers:",sum(1 for o in i("frontendOpenOrders") if o.get("isTrigger")))
PY'
```
Expect ≥1 resting trigger per open position. ZERO = deploy didn't run or stops still not firing.

---

## 🟡 WAITING ON JAMES (he chooses)

1. **Grant codex/ssh perms** — to let the AI run builds + the deploy unattended, James pastes this
   into `~/.claude/settings.json` under `permissions` (the AI is hard-blocked from doing it):
   ```json
   "allow": [
     "Bash(codex exec:*)",
     "Bash(bash tools/build_loop/run_codex.sh:*)",
     "Bash(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@198.54.123.234:*)"
   ]
   ```
2. **Always-on listener location** — Mac (default) or server — for the Ember-as-builder Telegram lane.

---

## 🟢 DONE (this session, all committed on feat/headless-build)

- **Build loop** — `tools/build_loop/run_codex.sh` (spec→build→review, worktree-isolated). Codex
  v0.139 on James's ChatGPT Max plan (`auth_mode=chatgpt`, $0 API).
- **Proof log + reversibility** — `core/BUILD/PROOF_LOG.md`, every action + one-command reverse.
- **Ember-as-builder lane** — James texts `build: <intent>` → `tools/queue/build_intent_router.py`
  captures to `core/BUILD/intents/` → Ember specs/builds/reviews. Wired into `daily_sync.py`. 5 tests green.
- **Reconciler + verdict tool** — `core/position_protection_reconciler.py`, `tools/whaletrack_verdict.py`
  built + merged (repo-local; NOT yet on prod — that's the deploy above).
- **World Scout** — reviewed PASS, already in the working branch.
- **deploy_reconciler.sh** — the one-paste prod deploy (the red focus above).

## 🟡 QUEUED FOR AI (no James needed)

- Review `feat/scout-caveman` (commit 30b82acb) → write `core/BUILD/reviews/`.
- Build Telegram `build`/`status` reply wiring once listener location is chosen.

---

## 📌 Live facts (verify before acting — may have changed)

- Whaletrack wallet `0xefbfead1189f32bc1000d3740445d0227286b77b` ≈ $431 (last read 2026-06-11).
- 2 open shorts (ETH, SOL), ~+$36 unrealized, **unprotected** until the deploy runs.
- Kill switch: `SWEEP_LIVE=1` (live). Halt: set `SWEEP_LIVE=0` on the systemd drop-in + restart.
- James loves the **buildstream-table** response format (🔴 focus / 🟡 your okay / 🟢 done). Keep it.
