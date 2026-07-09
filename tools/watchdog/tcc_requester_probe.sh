#!/usr/bin/env bash
# tcc_requester_probe — name the phantom TCC popup ("2.1.205" etc.)
# macOS shows a bare version string when the requester is an unsigned/nameless
# CLI helper. This probe catches the real process two ways:
#   1) lsof — what actually holds handles inside the watched Documents dirs
#   2) the unified TCC log — recent access/prompt events + responsible process
# Read-only. Writes findings to ~/.config/fpai/watchdog/tcc_probe.log.
set -u
LOG="$HOME/.config/fpai/watchdog/tcc_probe.log"
mkdir -p "$(dirname "$LOG")"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
WATCH_DIRS=(
  "$HOME/Documents/FPOS"
  "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Simple Brain"
)
{
  echo "===== $TS ====="
  echo "-- lsof: processes holding handles in watched Documents dirs --"
  for d in "${WATCH_DIRS[@]}"; do
    [ -d "$d" ] || continue
    lsof -w +D "$d" 2>/dev/null | awk 'NR==1 || $1!="" {print $1, $2, $3, $NF}' | head -40
  done
  echo "-- TCC unified log (last 15 min): prompts + responsible process --"
  log show --last 15m --style compact \
     --predicate 'subsystem == "com.apple.TCC"' 2>/dev/null \
     | grep -iE "prompt|documents|attribution|requesting|responsible|DocumentsFolder" | tail -30
  echo "-- live node/git MCP helpers (likely requesters) --"
  ps aux | grep -iE "mcp-server-filesystem|mcp-remote|simple-brain-sync|[n]ode .*server-filesystem" | grep -v grep | awk '{print $2, $11, $12, $13}' | head -20
  echo ""
} >> "$LOG" 2>&1
tail -60 "$LOG"
