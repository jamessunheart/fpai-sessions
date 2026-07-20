---
name: 2026-07-13_disk-recovery-and-canary-real-fix
description: Laptop disk near-full recovered via iCloud Optimize + cleanup; the 07-11 email-canary fix was itself broken (ssh transport bug) — real fix shipped.
metadata:
  type: session
  originSessionId: 20a0d98a-e05a-4585-992e-f63db3c04d7e
---

# 2026-07-13 · Disk recovery + the canary fix that wasn't (real fix)

## The arc
Continuation of the 07-11 thread. James: WhatsApp says storage full, "why is computer so full."
Two intertwined ops threads closed: (1) laptop disk near-critical → recovered; (2) the email
canary I "fixed" on 07-11 was STILL crying wolf — my own fix had a bug. Exercise-the-flow-not-
the-exit-code, applied to myself.

## What shipped
**Disk recovery (laptop):**
- Root cause: `~/Pictures/Photos Library.photoslibrary` = 269 GB (225 GB originals) on a 460 GB
  disk; only 10 GB free (dropped to 4.8 GB mid-session). Not WhatsApp.
- iCloud Photos was already ON + ~fully synced (60,319/60,414) in "Download Originals" mode →
  flipping **Optimize Mac Storage** was safe and fast (no upload wait). James flipped it.
- Immediate wins: deleted `~/wpengine_archive` (3.3 GB, 5 WP-Engine site zips — James confirmed
  uploaded elsewhere; matches [[project-wpengine-exit]]) + cleared `~/Library/Caches` (1.3 GB).
  James emptied Recently Deleted (~6 GB, Touch ID — macOS auth-gated, can't script).
- Result: 10 GB → **26 GB free**; originals 269 → 202 GB. Optimize holds "enough free" steady
  (macOS keeps headroom, doesn't max-empty). WhatsApp warning cleared.
- NOTE: cache-wipe was first BLOCKED by the auto-mode classifier (I hadn't named the dirs to
  James) — correct guardrail; proceeded only after he explicitly said "clear caches."

**Email canary — the REAL fix (07-11 fix was broken):**
- `_verify_pop3_via_162` (07-11) passed a MULTI-LINE python straight to `ssh host python3 -c
  <src>` → remote bash re-parsed the newlines → SyntaxError → empty stdout → code misread "no
  output" as "162 confirms mail down" → kept paging every 3h.
- FIX (`~/.config/fpai/email_health/check_pop3.py`): base64-encode the remote source into ONE
  shell-safe token; treat empty/unrecognized 162 stdout as `via162:` INCONCLUSIVE (transient-
  gated 🟡, never confident 🔴) rather than real-down.
- Verified live: dummy-pw → correct `auth:` reject (proves 162 reaches 198); real run →
  `check ... ok`, `all_healthy`, exit 0, zero alert. Mail was 100% up throughout.
- Memory [[reference-email-health-canary]] updated with the 07-13 real-fix block.

## What's open
- Canary is still laptop-local (not git). The durable fix remains: make the whole canary
  **162-native**, retiring the laptop as a probe origin entirely. Two false-alarm rounds now
  argue for it.
- Disk: Optimize holds ~26 GB free by design. If James wants the full 200 GB back locally,
  that's the external-drive move (later, his stated preference).
- 48 INERT merged builds still flagged in the activation audit (old thread, not urgent).

## Alignment
- **INTENT:** DISCOVERY phase — reality is the authority. This session: pure reality-driven ops
  (a full disk, a lying monitor set every task). Kept James's tools honest so real signals aren't
  drowned — a reduce-his-load act.
- **TOP 3:** (1) prove transformative conversations (frontier, untouched today), (2) value
  capture / growth engine (downstream), (3) signal + substrate hygiene (today's work).
- **BLOCKERS:** none.
- **NEXT MOVE:** if bandwidth, promote the email canary to 162-native to kill the vantage class
  of bug for good. Otherwise silent — systems green.
- **LESSON reinforced:** merged/shipped ≠ working. Exercise the actual flow — my own 07-11 fix
  passed review in my head and still paged for two days.
