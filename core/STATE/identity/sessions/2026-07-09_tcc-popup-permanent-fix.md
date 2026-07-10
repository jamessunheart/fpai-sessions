---
name: episodic-2026-07-09-tcc-popup-permanent-fix
description: The "2.1.204" macOS TCC popup recurred. Corrected yesterday's npx theory — the Claude Desktop MCP filesystem servers already use ABSOLUTE paths, not npx. Real cause = node reading TCC-protected iCloud+Documents vaults + the filesystem-server version auto-updating (shown as "2.1.204"). Permanent fix = grant /usr/local/bin/node Full Disk Access once. Opened the pane for James.
metadata:
  node_type: memory
  type: project
  originSessionId: 53bbd83c-7f54-45f0-b152-30b68aa2f6dc
---

# 2026-07-09 · The "2.1.204" TCC popup — permanent fix

## The arc
James sent the popup screenshot again — `"2.1.204" would like to access data from other apps` — with **"STOP CLAUDE, stop the hook, STOP IT."** He thought Claude Code was opening files. It isn't. Same Simple Brain MCP stack from [[episodic-2026-07-08-sunheart-chat-and-tcc-popups]]. He said "you decide" → I decided and executed the permanent fix.

## Correction to yesterday's diagnosis
Yesterday I blamed **npx re-resolving node** each launch. **Wrong.** Reading `~/Library/Application Support/Claude/claude_desktop_config.json` today: both filesystem servers already call an **absolute** binary — `/Users/jamessunheart/.npm-global/bin/mcp-server-filesystem` — pointed at the iCloud Obsidian vault (`My Simple Brain`) + `~/Documents/FPOS`. No npx in the config.

**Real cause:** `node` (`/usr/local/bin/node`) reads TCC-protected locations (iCloud Drive + Documents). macOS TCC identifies the requester by the node binary's code signature. The `mcp-server-filesystem` npm package **auto-updates its version** (the "2.1.204" shown in the prompt IS that package version) → each update changes what TCC sees → re-prompt. Hence the recurrence.

## What shipped
- **Decision + fix**: grant `/usr/local/bin/node` **Full Disk Access** → version updates become irrelevant, popups stop forever, vault access still works. Opened the FDA pane for James: `open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"`.
- Handed James the one irreducible GUI step (add node via `⌘⇧G` → `/usr/local/bin/node` → toggle ON → restart Claude Desktop). TCC is SIP-locked — **cannot** be scripted; this click is genuinely YOU-tier.
- This episodic.

## Then — Mac disk was 96% full (WhatsApp "Storage too full", 179MB)
Right after the popup fix, James hit a WhatsApp `Storage is too full` notice on the Mac. Diagnosed: `/` was **96% full — only 603MB free** on the 460GB disk. Biggest reclaimable = `~/Library/Caches` (6G) + `~/.cache` (1.5G) + `~/.npm/_cacache` (1.2G) — all regenerate. James approved. Cleared them → **603MB → 9.2GB free** (~8.6GB reclaimed). WhatsApp unblocked. Downloads (4.3G) left untouched (user data) for a later pass. Note: first `rm -rf` attempt was blocked by the auto-mode classifier (correct — bulk delete); ran only after explicit "I approve."

## What's open
- ★ **James action**: complete the FDA toggle for node + restart Claude Desktop. Unverified until he confirms popups stopped.
- Downloads folder (4.3G) — optional deeper cleanup later; the disk-full root cause (heavy caches) will recur, consider a periodic cache-sweep.
- **Fallback if it persists**: strip the two filesystem MCP servers (`simple-brain-vault`, `fpos-vault`) from the Claude Desktop config — but that kills Claude Desktop's live vault-edit path ([[reference_simple_brain_chat_stack]]), so only if James doesn't use Desktop-in-vault.
- Sunheart.com chat + landing deploy — still open from 2026-07-08, untouched this session.

## Alignment
- **INTENT**: Stop the macOS popup interruptions for good with zero recurring James-attention cost.
- **TOP 3**: (1) FDA-grant node → popups stop (James's one click). (2) Sunheart.com chat proxy + widget. (3) Deploy landing + wire lead pipe.
- **BLOCKERS**: FDA grant is James-only (OS security boundary, un-scriptable). Fix unverified until he confirms.
- **NEXT MOVE**: Wait for James's confirm; if popups persist, strip the filesystem servers.
