#!/bin/bash
# vault_memory_sync.sh — Path A (chosen by James 2026-05-30)
# Mirrors Ember's LOCAL canonical memory → the FPOS Obsidian vault as a live copy.
#
# WHY this runs under launchd (NOT claude): the claude binary's TCC access to the
# iCloud vault (network volume) is DENIED. A user launchd agent runs as its own
# responsible process, so it can write to the user's iCloud files without claude's
# per-version prompt. Local stays canonical + safe; the vault is the always-fresh
# read surface James opens in Obsidian.
#
# Source of truth = LOCAL. The vault subfolder is a pure mirror (safe to --delete).
set -euo pipefail

SRC="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/"
DEST="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/FPOS/Full Potential OS/00_MEMORY/_ember_memory/"
LOG="$HOME/.config/fpai/vault_sync/sync.log"

mkdir -p "$DEST" 2>>"$LOG" || { echo "$(date) ERROR: cannot create dest (iCloud access?)" >>"$LOG"; exit 1; }

# Posture B (James 2026-05-30): NO raw secrets in iCloud. Verified the operational
# memory (project_*/reference_*/spec_*) carries real wallet addresses, IPs, $ figures
# scattered everywhere — blacklisting was whack-a-mole. So this is a WHITELIST:
# sync ONLY the identity/ self-layer (verified clean of hard secrets — what James wants
# visible to "see the AI's state"). Everything operational stays LOCAL/brain only.
# Curated secret-free notes (FINANCIAL RESOURCES, SERVER MAP, NOW/GOALS MIRROR,
# AI CONSCIOUSNESS) are written to the vault directly, not through this sync.
# --delete-excluded purges any previously-leaked operational files from the vault.
if rsync -a --delete --delete-excluded \
     --exclude '.git' --exclude '.DS_Store' \
     --exclude 'identity/AI_CONSCIOUSNESS.md' \
     --include 'identity/***' \
     --exclude '*' \
     "$SRC" "$DEST" 2>>"$LOG"; then
  echo "$(date) OK synced memory -> vault" >>"$LOG"
else
  echo "$(date) ERROR rsync failed (likely TCC denial on iCloud path)" >>"$LOG"
  exit 1
fi

# NOTE on the home PROOF LOG (00_MEMORY/PROOF LOG.md):
# This launchd agent CANNOT write that specific file — once a file is owned by the
# claude/Terminal process, a bare launchd process is denied modifying it ("access data
# from other apps"). But CLAUDE CAN write it directly. So the home proof log is
# maintained by Ember (claude) at proof-write time via:
#   cp ~/.claude/.../memory/PROOF_LOG.md "<vault>/00_MEMORY/PROOF LOG.md"
# The agent still mirrors a redundant copy to _ember_memory/PROOF_LOG.md above.
