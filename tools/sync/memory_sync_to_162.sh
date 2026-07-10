#!/usr/bin/env bash
# memory_sync_to_162 · periodic keep-162-fresh job (revived 2026-07-09).
#
# The one-branch era (2026-07-03) moved memory/identity sync to git: work is
# committed on the laptop and pushed to 162's live checkout. This job runs that
# push every 30 min so committed work propagates to 162 BETWEEN settles (162's
# HOT_STATE + phone-Ember read from there).
#
# Deliberately does NOT auto-mirror runtime identity into the repo working tree:
# that would create uncommitted diffs a parallel session could bundle into its
# commit (the collision bug in CLAUDE.md). Identity mirroring stays a settle step.
#
# Best-effort + idempotent. Skips silently when offline or nothing to push.
# The original script was never git-tracked and vanished, leaving the launchd job
# exiting 127 for weeks (invisible until the watchdog learned to read exit codes).
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO" || exit 0

# Nothing to do if 162 is unreachable — transient, not a real failure.
if ! ssh -o ConnectTimeout=8 -o BatchMode=yes root@162.0.208.88 true 2>/dev/null; then
  echo "$(date -u +%FT%TZ) 162 unreachable — skip"
  exit 0
fi

# Push committed HEAD to 162 via the maintained one-branch mechanism.
bash "$REPO/tools/sync/settle_push.sh"
exit 0
