#!/usr/bin/env bash
# health_check.sh — make SILENT DEGRADATION LOUD (the cross-lab council's #1 fragility, 2026-06-15).
# The autonomous loops are brittle wrappers around subscription CLIs + systemd + worktrees: auth can
# expire, timers can drift, worktrees can stick, disk can fill — all silently. This checks each and
# logs any rot to the ops truth ledger (event=failed), so the morning digest's 🔴 fires + the bot's
# system-state surfaces it. Lightweight (no live model call). $0. Run every few hours via systemd.
# Kill: touch /opt/fpai-build/.health_disabled
set -uo pipefail
[ -f /opt/fpai-build/.health_disabled ] && exit 0
OL=/opt/fpai-build/FPAI_Cockpit/tools/build_loop/ops_log.py
fail(){ python3 "$OL" health failed "$1" '$0' '' "$2" 2>/dev/null || true; echo "FAIL: $1"; }

# 1. claude review token present + non-empty (the review engine's auth)
t=$(grep -o 'sk-ant-oat[^ ]*' /root/.config/fpai/claude.env 2>/dev/null | head -1)
[ -n "$t" ] || fail "claude review token missing/empty in /root/.config/fpai/claude.env" "Ember/James: re-run claude setup-token on 162"

# 2. recent auth errors in the loop/council journals (catches token rejection without a live call)
if journalctl -u fpai-build-loop.service -u fpai-council.service --since '6 hours ago' --no-pager 2>/dev/null \
     | grep -qiE 'invalid bearer|not logged in|unauthor|401 '; then
  fail "auth-rejection errors in build/council journal (last 6h)" "Ember: verify claude -p auth on 162"
fi

# 3. codex present (the build engine)
command -v codex >/dev/null 2>&1 || fail "codex CLI missing on 162" "Ember: reinstall codex"

# 4. the loops' timers active
for tm in fpai-build-loop fpai-council fpai-morning-digest; do
  [ "$(systemctl is-active "$tm".timer 2>/dev/null)" = active ] || fail "$tm.timer not active" "Ember: systemctl restart $tm.timer"
done

# 5. stuck/accumulating build worktrees (>24h old = likely unmerged/stuck)
stuck=$(find /opt/fpai-build/worktrees -maxdepth 1 -mindepth 1 -type d -mtime +1 2>/dev/null | wc -l | tr -d ' ')
[ "${stuck:-0}" -gt 4 ] && fail "$stuck build worktrees >24h old (stuck/unmerged)" "Ember: run reap_worktrees.sh --apply"

# 6. disk
use=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
[ "${use:-0}" -gt 85 ] && fail "disk ${use}% full on 162" "Ember: free disk on 162"

echo "health check done $(date -u +%H:%M)Z"
