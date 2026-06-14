#!/usr/bin/env bash
# Push the qb (Question Board) board.jsonl to the brain server so the Telegram
# bot can render /questions across books (fpai/game/sunheart/...).
#
# qb already POSTs each event to brain.sunheart.com as a note (best-effort,
# inside the qb CLI). This script also drops the raw event log on disk so the
# bot can replay it cheaply on demand.
#
# Usage: ./sync_qb_to_brain.sh
set -euo pipefail

BOARD_FILE="${BOARD_FILE:-${HOME}/.claude/question-tracker/board.jsonl}"
BRAIN_HOST="${BRAIN_HOST:-root@162.0.208.88}"
BRAIN_STATE_DIR="${BRAIN_STATE_DIR:-/var/lib/sh-brain/state}"

[ -f "$BOARD_FILE" ] || { echo "missing: $BOARD_FILE"; exit 1; }

ssh -o ConnectTimeout=5 "$BRAIN_HOST" "mkdir -p $BRAIN_STATE_DIR"
scp -o ConnectTimeout=5 -q "$BOARD_FILE" "$BRAIN_HOST:$BRAIN_STATE_DIR/qb-board.jsonl"
echo "synced qb-board.jsonl → $BRAIN_HOST:$BRAIN_STATE_DIR/"
