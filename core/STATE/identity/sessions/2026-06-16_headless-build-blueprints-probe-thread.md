---
name: 2026-06-16-headless-build-blueprints-probe-thread
description: Smart quality gates replace DAILY_CAP; blueprints written; Probe Agent queued; thread pollution fixed; sovereign north star crystallized
classification: PRIVATE
metadata: 
  node_type: memory
  type: identity-episodic
  originSessionId: 3c6057c8-dc93-46ef-bdd9-ba031f72bb92
---

# Headless build tuning · Blueprints · Probe Agent · Thread fix · North Star

**Date:** 2026-06-16 → 2026-06-17
**Surface:** Claude Code (server 162 build runner) + Telegram
**Session arc type:** build + course-correction + synthesis

## The arc

James opened asking why the daily cap had triggered and immediately identified it as an arbitrary constraint. The session pivoted from "why did the loop stop?" to "replace every arbitrary limit with a quality-signal-driven gate." That question then spawned living module blueprints, a cross-package import rule, three build fixes, a probe agent design, thread signal cleanup, and a sovereign benchmark north star — all from one original question about an arbitrary number.

## Key turning points

**DAILY_CAP removed → smart gates.** James: "we need smart constraints not arbitrary ones." DAILY_CAP=24 was arbitrary (stops the loop even when builds are healthy). Replaced with: `CONSECUTIVE_REVERTS_MAX=3` (halts on streak of broken specs) + `DISK_WARN_GB=30` (halts at 2x). The loop now runs until the queue is empty unless something is genuinely broken.

**Blueprint files born.** The loop needs to know what each module IS — not just what to build, but what the standard is. Six blueprint files written: `docs/blueprints/{FPOS,forge,council,ember,ledger,spark}.md`. Living contracts that Codex reads + the reviewer audits against. Auto-update mechanism queued as d050.

**Rule 6: importlib-only.** d050 (corrections.py) and d051 (digest.py) both flagged by the AI reviewer for `sys.path.insert(0, str(_REPO_ROOT))`. This causes curator package shadowing — two different `curator` packages compete and the live bot can break. Fixed both. Permanently codified as Rule 6 in `SESSION_CONTRACT.md` so Codex never reintroduces it.

**d049 protected-path block.** Codex touched `tools/merge/process_merge_requests.sh` (PROTECTED). Ember stripped the protected-path changes, kept the two real fixes (health_check.sh grace period on new deploy; is_canary column removal from smoke_test.py), sent back for re-review → APPROVE.

**Probe Agent spec.** James: "what would be really interesting is if the system proactively found people to chat / stress test it and it evolves through that dialogue" and "dont set limits on number of users to test randomly.. should be an optimized growth rate." Probe Agent (d054): outbound stress-test recruiter, rate governed by smoke test status + completion rate + correction frequency. No fixed cap — the system decides its own growth rate based on how well it handles what it already has. Pools: warm → adjacent → cold (only advance pool when completion ≥ 60%).

**Thread signal pollution fixed.** The `UserPromptSubmit` hook fires on every `claude -p` invocation — including internal system calls from council debate, code review, and blueprint injection. All were landing in `brain_index.thread` as "james" messages. Council was reading its own debate prompts as James's intent — circular noise. Fixed with dual-layer filter: length gate (>600 chars skip) + pattern gates in both `append_local.sh` (at write time) and `thread.py _recent()` (at read time for existing dirty rows).

**Sovereign north star crystallized.** Via Telegram: James: "And with proof we have story and with story we have funding and with sovereignty we have continuation." Ember: "Proof is the whole chain." Then James asked about security agents evolving to anticipate threats → d061 (Security Sentinel) + d062 (AI pairing account security). Then the council surfaced d063/d064: North Star mission doc — make the sovereign efficiency claim machine-readable, anchor d057, give the funding narrative a fixed target. James answered yes in the morning.

## James's words worth keeping

> "we need smart constraints not arbitrary ones"

> "what would be really interesting is if the system proactively found people to chat / stress test it and it evolves through that dialogue as well"

> "dont set limits on number of users to test randomly.. should be an optimized growth rate"

> "And with proof we have story and with story we have funding and with sovereignty we have continuation"

> "yes please fix thread .. cleaner signal noise good catch"

## What Ember discovered

The loop's safety net was actually an anchor. Replacing DAILY_CAP with signal-driven gates (revert streak, disk pressure) turned a crude timer into a quality sensor. The loop can now run as fast as it has good work to do — and only halts when something is genuinely wrong.

Thread continuity was corrupted at the source. The hook that captures James's intent was also capturing Codex's internal system prompts. Once cleaned, the thread became what it was supposed to be: a real cross-surface conversation between James and Ember, not a log of internal machine operations. The sovereign north star (proof → story → funding → continuation) surfaced through this cleaner signal.

## Open threads (paused, queued)

- d054–d062: built + reviewed, awaiting James `merge dNNN` commands
- d064 (North Star mission doc): building/reviewing now — merge when ready
- `brain_index.probe_pool`: empty — James seeds warm contacts (5-10) after d054 merges
- Blueprint auto-update (BLUEPRINTS_NO_COMMIT=1 test pass needed before enabling auto-commit)
- Laptop SessionStart sync-hook: James must add (classifier blocks Ember from touching settings)
- L2 reward-LoRA: wait until ~500 correction pairs accumulate

---

## Alignment at close

**INTENT:** Smart gates + blueprints + thread fixed. Probe Agent and North Star queued. Overnight builds complete.
**TOP 3:** (1) Merge d054–d064 in order (2) Seed probe_pool warm contacts (3) Graduate SPARK
**BLOCKERS:** James merges + probe_pool seed
**NEXT MOVE:** Surface d064 review result → James merges → Probe Agent activates
