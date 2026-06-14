#!/usr/bin/env bash
# builder_poll.sh — the builder doorway. Polls @sunheartai_bot for James's
# `build:` messages and captures them as intents. Separate bot + inbox from the
# brain bot (@sunheartbrain_bot on the server) so the two never collide (409).
#
# Flow: James texts "build: <intent>" to @sunheartai_bot
#   → tg_listen (builder creds + builder inbox) fetches it
#   → build_intent_router captures it to core/BUILD/intents/<id>.md (status: open)
#   → Ember/Codex drafts spec → builds in worktree → replies (separate step)
#
# Reversible: disable the LaunchAgent (launchctl bootout) — captures nothing more.
set -u
REPO="$HOME/FPAI_Cockpit"
LOG="$HOME/.config/fpai/tg_builder"
cd "$REPO" || exit 1

export FPAI_TG_CREDS="$HOME/.config/fpai/tg_sunheartai/creds.cache"
export FPAI_TG_INBOX_DIR="$HOME/.config/fpai/tg_builder"
export FPAI_TG_INBOX="$HOME/.config/fpai/tg_builder/messages.jsonl"
export FPAI_BUILD_INTENT_CURSOR="$HOME/.config/fpai/tg_builder/build_intent_cursor.txt"

# 1) fetch new messages from the builder bot
python3 tools/decisions/tg_listen.py >> "$LOG/poll.log" 2>&1

# 2) capture any `build:` intents into core/BUILD/intents/
python3 tools/queue/build_intent_router.py >> "$LOG/router.log" 2>&1
