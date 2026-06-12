# Codex Phone / Cloud / SSH Handoff

This is the portable handoff for Codex runs that may not have James's Mac,
iCloud vault, local config, or unpushed worktree.

## Read Order
1. `AGENTS.md`
2. `docs/codex/README.md`
3. `docs/codex/AI_PROTOCOLS.md`
4. `docs/codex/HANDOFF.md`
5. `docs/codex/ATTENTION_FLOW.md`
6. Target spec in `docs/codex/specs/`, if James explicitly names one.

## Surface Choice
- **Mac / laptop Codex:** local truth. Use for vault, local config, credentials,
  screenshots, unpushed files, first-time setup, and high-risk approvals.
- **Phone controlling Mac host:** same environment, smaller interface. Use for
  steering, review, approvals, and continuing an active Mac thread while the Mac
  is awake and connected.
- **Phone Codex Web / Cloud:** GitHub-only Buildstream. Use when the Mac is
  unavailable. Work only from pushed branches and repo mirrors.
- **SSH Codex Build Host:** optional always-on repo builder. Use one dedicated
  low-privilege dev host, not a production service host. Keep it repo-first.

If a phone run asks for SSH, it is starting remote-host setup. That is optional;
normal fallback is GitHub/cloud.

## Current Portable State
- Branch with latest portable instructions: `feat/financial-hub`.
- Financial Hub is built and pushed on this branch.
- `docs/codex/AI_PROTOCOLS.md` is the current doctrine mirror for the Layer-3
  Intelligence Engine.
- The system is moving toward self-standing FPOS:
  Coherence -> Attention -> Intelligence -> Resources -> Humans -> Proof ->
  Better Intelligence.
- Next self-standing ladder item is **Rung 1: Auto-proof**, but it is gated:
  do not build it until James/Ember provides or blesses `SPEC_auto-proof`.
- Comms Hub remains a possible James-facing next signal, but if it conflicts
  with the self-standing ladder, ask James/Ember which to run first.

## Phone / Cloud Operating Rules
- Work repo-only unless James explicitly grants a broader lane.
- Do not assume access to Obsidian/iCloud, `~/.config/fpai`, local secrets,
  screenshots, unpushed files, or the Mac worktree.
- If vault updates are needed, write the request into `docs/codex/HANDOFF.md`
  under Questions for Ember/James.
- Never move money, send outreach, stop/delete services, deploy production, or
  make irreversible changes.
- Before building, summarize the handoff and ask for James's go.

## Kickoff Prompt
```text
Continue FPAI_Cockpit from GitHub branch feat/financial-hub.

Read AGENTS.md, docs/codex/README.md, docs/codex/PHONE_HANDOFF.md,
docs/codex/AI_PROTOCOLS.md, docs/codex/HANDOFF.md, and
docs/codex/ATTENTION_FLOW.md.

Assume this may be phone/cloud/SSH mode. Work repo-only unless I explicitly
grant a broader lane. If vault/iCloud updates are needed, post requests in
docs/codex/HANDOFF.md for Ember/Claude to mirror.

Do not touch money, outreach sends, service stops/deletes, production deploys,
secrets, or irreversible actions.

Before building anything, summarize what the handoff says, name the next
allowed build only if a spec exists, and ask for my go.
```
