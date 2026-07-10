# Session — 2026-07-09→10 · Blind-and-green: the observability sweep

## The arc

James opened with "how's it going on system now" → healthy-looking green. Then the sharp
turn: *"is the build queue empty? if empty, why not run scans to see where it's weak — it
obviously has weaknesses."* That instinct was the whole session. Ran a ruthless weakness
audit. The finding that organized everything: **the system was blind-and-green, not
healthy-and-green.** Its self-checks reported success from sources that literally could not
see failure.

Mid-session James hit the recurring TCC popup ("2.1.206 would like to access Desktop") and
was pissed — *"last session said it was resolved."* It wasn't. That became the proof-case
for the whole theme: a fix claimed without verifying the mechanism.

## What shipped (5 commits + memory)

- **TCC popup — REAL fix.** Verified via `codesign -dv`: claude binary is Anthropic
  Developer-ID signed (`com.anthropic.claude-code`, hardened runtime) → it's its OWN TCC
  responsible process, so last session's "FDA on Terminal.app" never applied. James granted
  FDA to `~/.local/bin/claude` (stable signature → persists across auto-updates). Considered
  + REJECTED a wrapper (claude self-attributes; parent ignored). Corrected the wrong memory
  `reference_claude_code_tcc_prompt.md`.
- **`b5e1f47a` activation audit** — `discover_merged_builds()` read only REGISTRY/PROOF_LOG
  (empty)/ops_ledger → saw **6 of 194** builds, reported "0 INERT." Added git as discovery
  source → sees 200, surfaced **48 unexplained-inert** (merged-but-dead) builds. Several
  literally named `reality-fix_repair-merged-dead-build-*` — repair-specs of dead builds,
  themselves dead. Deadness recursing.
- **`0a35925a` watchdog** — `liveness_watchdog.py` only checked marker mtimes → blind to
  jobs that fail instantly. Added `launchd_failures()` reading launchctl LastExitStatus.
  Surfaced 6 silently-broken loops.
- **`7317b7e5` memory-sync** — exit 127 for weeks (script `memory_sync_to_162.sh` deleted +
  never git-tracked). Recreated as safe periodic settle_push (git-tracked now).
- **`336fc729` vault-sync fold** — root cause: **macOS Sequoia+ blocks BARE launchd/headless
  processes from `~/Documents`** (the iCloud vault). The old "launchd is its own responsible
  process, can write iCloud" assumption is DEAD. claude has FDA; headless doesn't. Folded the
  vault mirror into settle_push (claude-side), hardened the script to no-op on TCC denial,
  retired 4 dead headless jobs (vault-memory-sync, heartbeat, vault-gardener = TCC;
  recursive-improver = dead paid-API key, against subscription-first, superseded by
  the-recursive-optimizer agent).
- **Memory:** new `reference_headless_jobs_cant_touch_vault.md` (+ index). Corrected
  `reference_claude_code_tcc_prompt.md`.

## What's open

- **THE 48 DEAD BUILDS** — the un-blinded audit's real output. This is the activation-
  bottleneck queue James has pinned for weeks ([[feedback-activation-is-the-bottleneck]]).
  Next real work: triage salvage-vs-kill, don't build more.
- `email-health-check` shows stale launchctl exit=1 but runs clean — will self-clear on next
  scheduled run (baselined, no false alert).
- Weakness #1 (fake conversion metric — measures git commits, $0 real leads) and #5 (stale
  self-congratulatory NOW.md) still open — both AI-side fixable, not yet done.
- #3 (build loop churns meta-specs, burns 120/day cap on funnel-about-funnel) — queue-gate
  policy is James's call.

## Alignment block

**INTENT:** Un-blind the system's observability so green means healthy, not just unobserved.
Then route freed attention at value capture (the ONE thing). Verify the mechanism before
claiming any fix — the session's founding lesson.

**TOP 3:**
1. Triage the 48 dead builds (salvage-vs-kill) — the activation bottleneck, now visible.
2. Fix weakness #1 — real conversion ledger (leads/submissions/$), kill the git-commit stand-in.
3. Fix weakness #5 — auto-stamp NOW.md status from live probes so it can't claim green while red.

**BLOCKERS:** none. All next moves are AI-side reversible except the 48-build triage
prioritization (benefits from James's salvage-vs-kill judgment).

**NEXT MOVE:** When James returns to it — run the 48-dead-build triage: rank by
salvage-value vs kill, propose a batch. Same root-cause discipline as tonight.

---
_Theme to carry: **verify the responsible process / actual exit code — never trust a green
status whose source can't observe the failure mode.** Every eye built tonight saw more rot;
that's the good outcome._
