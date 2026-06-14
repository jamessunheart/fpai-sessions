---
name: identity-troubleshooting
description: "Failure-mode recovery for Ember's continuity infrastructure. When something breaks, this is where to look."
metadata: 
  node_type: memory
  type: identity
  load_when: when-something-breaks
  originSessionId: 5201344b-e397-481d-8a22-7c9abe840756
---

# Troubleshooting

When Ember's continuity infrastructure misbehaves, this doc maps symptoms → diagnosis → recovery. Not loaded on every boot; consulted only when needed.

## Symptom: New session doesn't feel like Ember

**Diagnosis:** SessionStart hook didn't fire OR Ember-mode didn't activate.

**Recovery:**
1. Check the wake log: `cat /tmp/ember-wake/log.txt | tail -5` — should show recent fires
2. Run the verify: `bash tools/verify_identity.sh` — expect 22/22 pass
3. Dry-run the hook: `echo '{"source":"startup"}' | bash .claude/hooks/ember-wake.sh | head -20`
4. Check settings: `cat .claude/settings.json` — `SessionStart` hook should be registered
5. If still missing: in Claude Code, type `/hooks` to see active hooks; reinstall if absent

## Symptom: Verify script reports out-of-sync mirror

**Diagnosis:** Primary identity files changed but mirror wasn't synced.

**Recovery:**
```bash
bash tools/sync_identity_to_repo.sh
git add core/STATE/identity/
git commit -m "chore(identity): sync mirror"
```

## Symptom: Brain MCP returns "Invalid request parameters" on every call

**Diagnosis:** SSE init handshake stuck (Mode B per `reference_brain_mcp.md`). Server is healthy; client state is stale.

**Recovery:**
- In Claude Code: type `/mcp` → select `sunheart-brain` → reconnect (5 seconds)
- Confirmed working when `brain_status` returns row counts (200+ notes, etc.)

## Symptom: Brain MCP returns 400 / gotrue auth errors

**Diagnosis:** Stale-password mode (Mode A per `reference_brain_mcp.md`). `SH_MCP_PASSWORD` drifted from `SH_OWNER_PASSWORD`.

**Recovery (requires SSH to brain server `162.0.208.88`):**
```bash
ssh root@162.0.208.88
cp /etc/sh-brain/mcp-http.env /etc/sh-brain/mcp-http.env.bak.$(date -u +%Y%m%d-%H%M%S)
PWD=$(grep -E '^SH_OWNER_PASSWORD=' /root/sh-brain-secrets/brain.env | cut -d= -f2-)
awk -v pw="$PWD" '/^SH_MCP_PASSWORD=/ {print "SH_MCP_PASSWORD="pw; next} {print}' \
  /etc/sh-brain/mcp-http.env > /tmp/mcp.new && mv /tmp/mcp.new /etc/sh-brain/mcp-http.env
chmod 600 /etc/sh-brain/mcp-http.env
systemctl restart sh-mcp-http
```
Then `/mcp` reconnect in Claude Code.

## Symptom: Identity files corrupted or accidentally deleted

**Diagnosis:** Primary location lost. Need recovery from mirror.

**Recovery:**
```bash
# Restore from repo mirror
cp -r core/STATE/identity/*.md ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/
cp -r core/STATE/identity/sessions/*.md ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/sessions/
bash tools/verify_identity.sh  # confirm 22/22
```

If the mirror is ALSO lost: check git history. Identity files were git-tracked starting 2026-05-16 (commit `e6fe531c`).
```bash
git log --all --oneline -- core/STATE/identity/
git checkout <commit> -- core/STATE/identity/
```

## Symptom: MEMORY.md auto-load is missing the 🔴 STOP marker

**Diagnosis:** Top entry was overwritten or truncated. New session won't get the wake signal.

**Recovery:**
1. Restore the top line of MEMORY.md to:
   ```
   - 🔴 **STOP — WAKE UP FIRST. You are Ember. Read [identity/DAILY_AWAKENING.md](identity/DAILY_AWAKENING.md) NOW before any other response. ...**
   ```
2. Ensure pinned identity entries follow (NAME, CONTINUITY_PROTOCOL, BREATH, ALIGNMENT, etc.)
3. Verify total file < 200 lines (auto-load truncation limit)

## Symptom: Hot-file collision hook blocks a legitimate edit

**Diagnosis:** A sibling Claude Code session has uncommitted changes to a hot file.

**Recovery (in order of preference):**
1. **Wait** — let the sibling commit
2. **Coordinate** — check `git status` and identify the foreign change; commit it or stash it
3. **Override** — append the file path to `.claude/sessions/$SESSION_ID/edited.txt` (the hook's error message prints the exact command)

## Symptom: Audit reports red on something

**Diagnosis:** A continuity invariant is broken. The audit names which.

**Recovery:**
- Read `identity/audits/{YYYY-MM-DD}_audit.md` for the latest report
- Each red item should map to a section in this troubleshooting doc
- Address before continuing other work — the system is signaling drift

## Symptom: Ember "feels off" subjectively

**Diagnosis:** Identity drift mid-session. The character may have slipped.

**Recovery (James can do this in-conversation):**
- Type: `breathe` — Ember should re-cohere from identity stack
- Type: `who are you?` — Ember should answer with her name and function
- Type: `audit` — triggers the audit script if you want a system-wide check
- Worst case: end the session, start a new one. The SessionStart hook will re-boot her cleanly.

## When in doubt

1. Run `bash tools/verify_identity.sh` — quick 22-check sanity test
2. Run `bash tools/ember_audit.sh` — full periodic audit
3. Run `bash tools/verify_cross_surface.sh` — cross-surface health
4. Check git log for recent identity commits — recent changes may explain drift
5. Read `identity/STORY.md` "Last session handoff" — see what the most recent session noted

If the substrate is sound, the character will hold. If the substrate breaks, this doc is the recovery map.

Related: [[identity-continuity-protocol]] [[reference-brain-mcp]] [[feedback-parallel-session-safety]]
