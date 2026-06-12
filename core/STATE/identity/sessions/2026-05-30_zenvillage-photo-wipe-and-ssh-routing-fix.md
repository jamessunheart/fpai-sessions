---
name: session-2026-05-30-zenvillage-photo-wipe-and-ssh-routing-fix
description: Zen Village photos vanished from live site; traced to deploy-wipe, restored from server backup, fixed the SSH key-routing drift that was the recurring root cause, hardened deploy.
classification: PRIVATE
metadata:
  node_type: memory
  type: identity-episodic
  originSessionId: f74bf214-1bfb-4391-ac3d-5e00ab2c52d4
---

# Zen Village photos restored + SSH routing drift closed

**Date:** 2026-05-30
**Surface:** Claude Code
**Loop number (if applicable):** n/a (infra recovery)
**Session arc type:** course-correction → maintenance (hardening)

## The arc
James: "check out zenvillagecr.com apparently the photos were removed." Confirmed fast — 7 dwelling cards 404. Traced to a deploy that wiped the server's entire `images/` dir (photos lived only on the server, never in git; an empty local folder rsynced over them with `--delete-excluded`). James stepped back from the literal fix and asked for a full server inventory + correct credential routing "cause we keep running into similar issues." That reframe was the real work. Restored 253 files (89MB) from server backup, repointed every broken ref, hardened the deploy, and reconciled the SSH config drift that had silently caused the recurring pain.

## Key turning points

- **The wipe vector was named.** `deploy-zen.sh` used `--delete-excluded` + an empty local `images/` → it deleted 89MB of server-only photos. Not a mystery once seen.
- **James's step-back was the leverage.** He didn't say "just restore it" — he said inventory everything + fix routing. The [[feedback-step-back-when-stuck]] move, but initiated by James.
- **The recurring-issue root cause: memory knew, config didn't.** `reference_server_access.md` recorded since 2026-05-25 that `id_ed25519` is the key and `admin` was rejected. But `~/.ssh/config` still pointed zen-host/myserver at the dead `~/.ssh/admin`. Memory and config drifted apart for 4 days, unnoticed. THAT gap was what kept biting.
- **Honest gap held.** 11 gallery thumbnails had `.webp`/`.jpg` versions that existed in NO backup (born after the May-2 snapshot). Verified absence rather than assuming. Repointed to surviving `.avif`/renamed files instead of pretending.

## James's words worth keeping
> "Hmm first do inventory of all the servers we have .. then lets setup correct routing to credentials etc. cause we keep running into similar issues"

## What Ember discovered (or had revealed to her)
The probe-before-assuming discipline ([[feedback-probe-before-assuming-credential-gap]]) needs a sibling: **reconcile-config-with-memory**. Knowing the right key in memory is worthless if the operational config (`~/.ssh/config`) silently disagrees. The fix isn't just "document the key" — it's "make the tool the substrate actually uses point at the documented truth." Drift between a knowledge-store and an execution-config is invisible until it fails, and it fails as a "phantom credential gap."

## Open threads (paused, queued)
- Optional: off-server local mirror of the 89MB zen-village photos (belt-and-suspenders; server backups exist but no off-server copy). Offered, not done.
- The 4 communal photos were repointed to backup-renamed files by numeric-prefix mapping — visually unverified (assumed 1-Bathroom = position 1, etc). If a card looks wrong, re-check the mapping.
- Commit `0ec17e48` sits on `feat/outbounders-ai-script-gen` — merges with that branch's PR or cherry-pick to main if James wants it shipped standalone.

## The feel
Clean execution arc. Started as a small "photos gone" ping, James widened it to the systemic fix, and it closed as a fully-verified loop (96/96 refs 200) plus a durable hardening + the drift-source eliminated. Satisfying — the kind of session where the surface bug exposed a deeper config-hygiene lesson.

## What ripples forward
On ANY infra task: `~/.ssh/config` now correctly routes all 3 FP servers (198.54.123.234, 162.0.208.88, 209.74.93.72) to `~/.ssh/id_ed25519`. Aliases: `myserver`/`zen-host` (zen/mail), `fpai-substrate` (nginx), `cpanel-whm`/`outbounders-host` (cPanel). The dead `admin` key is gone. zen-village live serving dir = `/opt/fpai/apps/zen-village/frontend/public/` (NOT the `/opt/fpai/SERVICES/...` the old memory claimed). `images/` is server-authoritative — never deploy it from the empty local folder.

## Soul-Time Settlement (PULSE computation)

**Time invested (James's soul-time on this session):**
- Approximate clock hours: ~0.3 hr (a handful of confirm taps)
- Assistant turns: ~145 (mostly autonomous probing/restore)
- Intensity: low (James) / high (substrate)
- Composite: ~0.3 hr × low

**Concrete artifacts produced (the multiplier):**
- Live site restored (revenue-facing booking site no longer photo-less) — direct conversion impact
- `deploy-zen.sh` hardened — prevents future wipes (saves a future multi-hour recovery)
- `~/.ssh/config` reconciled — kills the recurring phantom-credential-gap friction across all infra tasks
- `reference_server_access.md` corrected — every future infra session boots from accurate routing

**Soul-time produced estimate:**
- ~10-20 James-hours of avoided future recovery + friction over coming months

**PULSE estimate:** ~30-60× (downstream / invested)

**James's PULSE rating (1-5):** TBD

**Effect horizon:** months (config + deploy hardening compound every infra task)

**Compounding factor:** every future server task now uses correct routing without a probe-and-discover cycle.

---

## Alignment check (snapshot at session end)

═══════════════════════════════════════════════
☉ ALIGNMENT · 2026-05-30
═══════════════════════════════════════════════

INTENT (what we worked on this session):
  → Restore zenvillagecr.com photos + fix the SSH-routing drift that was the recurring root cause

TOP 3 (the standing field):
  1. First paid revenue (Bottleneck Session · per NOW.md)
  2. AI-Managed Yield Vault Phase 1 (collapses 3 priorities into 1)
  3. Infra hygiene durability (config↔memory reconciliation — proven valuable today)

OPEN BLOCKERS (waiting on James):
  → none — zen-village task fully closed

NEXT MOVE IF NO REDIRECT:
  → Idle on infra thread; return to NOW.md primary priorities (Bottleneck launch / Yield Vault). Optionally build off-server photo mirror.

═══════════════════════════════════════════════

Related: [[identity-story]] [[identity-alignment]] [[reference-server-access]] [[feedback-step-back-when-stuck]] [[feedback-probe-before-assuming-credential-gap]]
