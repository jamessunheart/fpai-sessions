---
name: 2026-07-07_queue-builder-vault-blocked
description: Autonomous queue-builder run blocked — vault path outside allowed working dir + macOS TCC deny
metadata:
  type: project
---

# Session — 2026-07-07 · Queue-builder blocked on vault access

## Arc
Autonomous FPOS queue-builder fired on timer. Job: build at most one small,
safe, reversible markdown item from the vault queue. Could not start — the
vault is unreadable and unwritable from this runner.

## What happened
- Target files (`00_MEMORY/CHATGPT EMBER QUEUE.md`, `INTENT RADAR.md`,
  `AUTONOMY POLICY.md`) → **Read denied** (`EPERM: operation not permitted`).
- `ls` on `00_MEMORY/` → `Operation not permitted` (macOS TCC on iCloud dir).
- Append to `QUEUE BUILDER LOG.md` → **blocked**: vault path is outside this
  session's allowed working dir (`/Users/jamessunheart/FPAI_Cockpit`).
- Writes to the `~/.claude/.../memory/` mirror also blocked (sensitive-file
  prompt, non-interactive).
- Built nothing, wrote nothing to the vault, logged nothing. Conservative
  outcome preserved — no risky action.

## What shipped
- Nothing to the vault. This git-tracked session note is the only write.

## Open threads
- 🔴 Queue-builder runner has NO vault access. Two barriers: (1) session
  allowed-dir excludes the iCloud vault path; (2) macOS TCC blocks the
  iCloud Obsidian dir for this process. Needs James to grant Full Disk
  Access to the runner's host process AND/OR add the vault path to the
  session's allowed working directories. Until then every timer run is a
  no-op that can't even self-log to `QUEUE BUILDER LOG.md`.

## Alignment
- **INTENT:** run autonomous queue-builder safely.
- **TOP 3:** (1) restore vault access for the runner; (2) confirm the log
  path is writable so idle/blocked runs self-record; (3) resume normal
  one-item-per-run cadence.
- **BLOCKERS:** vault path outside allowed dir + TCC deny — needs James.
- **NEXT MOVE:** James grants access; re-run to confirm read+append work.
