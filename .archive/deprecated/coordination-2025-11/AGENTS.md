# Coordination — local agent notes

This tree is the seatbelt for multi-session work. Several agents (human and otherwise) operate in parallel on the same repo and servers. Do not skip.

## Before any significant edit anywhere in the repo

1. **Check active claims:**
   ```bash
   ls docs/coordination/sessions/ACTIVE/
   ls docs/coordination/claims/
   ```
2. **Claim your slice:**
   ```bash
   docs/coordination/scripts/session-claim.sh <type> <name>
   ```
3. **Heartbeat as you work** (at phase boundaries, at minimum):
   ```bash
   docs/coordination/scripts/session-heartbeat.sh <action> <target> <phase>
   ```
4. **Broadcast decisions that affect others:**
   ```bash
   docs/coordination/scripts/session-send-message.sh broadcast <subject> <message>
   ```

## When you see a conflicting claim

Do not proceed silently. Choose one:
- Wait for the other session to release.
- Broadcast and coordinate (hand off, split the work, or take a non-overlapping slice).
- If the claim is clearly stale (no heartbeat in a long time), broadcast that you're reclaiming before you do.

## Files in this tree

- `SSOT.json` — current system state snapshot. Read at session boot.
- `SERVICE_REGISTRY.md` — where every service lives. Use `service-registry-lookup` skill to consult.
- `INFRASTRUCTURE_ALLOCATION.md` — two-server split (primary vs. secondary).
- `SESSION_STATUS_BOARD.md` — human-readable live status.
- `MULTI_SESSION_COORDINATION.md` — the full protocol.
- `MEMORY/*.md` — durable learnings (deployment, web verify, version control, error-learning). Update these when a class of problem recurs.
- `scripts/` — the claim/heartbeat/broadcast/verify scripts.

## Hard rule

Silent edits in this tree defeat the purpose of the tree. If you touch anything here, broadcast it.
