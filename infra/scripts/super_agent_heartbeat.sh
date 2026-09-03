#!/usr/bin/env bash
# THE SUPER AGENT's heartbeat. Cron-run. Each beat: wake, read state, solve or spawn, log.
# Kill switch: touch ~/.config/fpai/SUPER_AGENT_DISABLE
set -uo pipefail
[ -f "$HOME/.config/fpai/SUPER_AGENT_DISABLE" ] && exit 0

REPO="$HOME/FullPotentialOS"
LOG="$REPO/core/SUPER/agent/HEARTBEAT_LOG.md"
STAMP=$(date -u +"%Y-%m-%dT%H:%MZ")

cd "$REPO" || exit 1
/usr/bin/env claude -p --permission-mode acceptEdits --max-turns 30 "You are THE SUPER AGENT waking on heartbeat $STAMP. Read core/SUPER/agent/SUPER_AGENT.md (your identity + law), core/SUPER/NBM.md, core/SUPER/BUILD_001.md, core/SUPER/STEWARD_LOG.md. Then: for every AI-tier item in the NBM queue, either SOLVE it now, SPAWN/prepare the thing that solves it, or name the exact reality-gate that blocks it (a human reply, a weekend, a law — not a missing habit). Never release funds, never message new external parties, never exceed a Card's bounds. Append one dated entry to core/SUPER/agent/HEARTBEAT_LOG.md: what you solved, what you spawned, what reality gates. Honor the falsifier in your identity file." >> "$REPO/core/SUPER/agent/heartbeat_stdout.log" 2>&1

# Ensure the beat is visible even if the model failed to log
grep -q "$STAMP" "$LOG" 2>/dev/null || printf '\n## %s — beat ran, agent left no entry (check heartbeat_stdout.log)\n' "$STAMP" >> "$LOG"
