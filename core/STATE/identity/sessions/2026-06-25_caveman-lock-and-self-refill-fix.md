---
name: 2026-06-25_caveman-lock-and-self-refill-fix
description: Locked caveman clarity as hard default across session-load surfaces · fixed the self-refill loop (24h→6h cooldown) and proved it generates builds on its own
metadata: 
  node_type: memory
  type: episodic
  date: 2026-06-25
  originSessionId: 0d65e1c4-bd80-4906-8ee2-656ed388c972
---

# Caveman lock + self-refill fix · 2026-06-25

## The arc

Started as a status check. James probed live state — I verified on 162 (awareness 42.2%, build loop healthy, queue empty). Then two real threads opened:

1. **Voice discipline.** James pushed hard, repeatedly, that my replies were *not* caveman enough. Each "still not caveman" was a correction. The lesson landed: stop narrating my thinking for myself, stop asking dumb yes/no questions to a caveman, lead with the answer, tiny footer only. He wanted it **consistent** and **saved so no session forgets**.

2. **Self-navigation gap.** The build queue was empty and sitting idle. James: "make smart scanner — find, build, good." I traced the loop: scanner → council → decision → build → review. Found the council self-refills via a `self_diagnostic` that fires on empty queue — but it was on a **24h cooldown** (last ran Jun 24 15:11, napping). Not broken — slow.

## What shipped

- **Voice locked in 3 load-every-session surfaces:**
  - `~/.claude/output-styles/caveman-3point.md` — banner at top + THE LOCKED SHAPE (1.Point 2.Options 3.tiny footer) that wins over the old verbose rules
  - `MEMORY.md` boot capsule — voice line near top
  - `feedback_caveman_clarity_output_contract.md` — marked caveman mode = ON standing default
- **SSH alias fixed:** added `162` as second name on `fpai-substrate` block in `~/.ssh/config` (the `162` shorthand in memory notes now actually resolves).
- **Self-refill fixed + PROVEN:** shortened `tools/council/self_diagnostic.py` cooldown 24h→6h. Woke the diagnostic live → **generated 3 new build specs, $0**. Committed on 162 as `ece7edd`. System now self-scans 4×/day when idle.
- **Forge revived (efficiency audit win):** James asked "full potential speed?" → audited 162, found 3 dead services. Forge daily+weekly both crashed: `auto-settle.sh` used `$HOME` under `set -u` but systemd has no HOME → unbound var; then "Not logged in" (no claude.env token in the unit). Fixed hook with `: "${HOME:=/root}"` + added `Environment=HOME=/root` + `EnvironmentFile=/root/.config/fpai/claude.env` to both forge units. **forge-daily proven exit 0, `status:ok`.** Committed `6d13f83`. forge-weekly now reaches the AI but parser fails ("no parseable findings") — smaller separate bug, left for the self-build loop.

## Honest catches

- Server-side CC had said "next: build d101/d102" — **stale**: both already built Jun 18. Caught it.
- The real gap was never d101/d102 (those tune the model). It was the refill *pace*.
- A laptop merge from `server162/feat/headless-build` left transient conflict markers in CLAUDE.md — resolved by the time I checked (false alarm).

## What's open

- Build loop will build the 3 fresh specs (~next run). Haven't verified they merged clean yet.
- James's last question: **"is the system running at full potential speed/efficiency?"** — not yet answered with a real audit. That's the live thread.
- MEMORY.md index is bloated (49KB > 24KB load limit) — entries drop on load. Compaction queued, not done.
- detect_correction_hook.sh still not added to laptop settings.json UserPromptSubmit.

## Alignment

- **INTENT:** System self-builds on its own cadence + Ember speaks caveman-consistent. Both shipped today.
- **TOP 3:**
  1. ★ Self-navigation loop — self-refill now 4×/day, proven. Next: confirm the 3 specs build+merge clean.
  2. ★ Bot awareness reliability → 100% — 42.2% live, climbing autonomously.
  3. First real conversation — OUTREACH_LIVE=1, autonomous.
- **BLOCKERS:** none. detect_correction_hook is a 2-min James task, not blocking.
- **NEXT MOVE:** Answer the full-potential-speed question with a real efficiency read, then watch the 3 specs build.
