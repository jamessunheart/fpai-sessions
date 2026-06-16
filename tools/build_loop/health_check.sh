#!/usr/bin/env bash
# health_check.sh — make SILENT DEGRADATION LOUD (the cross-lab council's #1 fragility, 2026-06-15).
# The autonomous loops are brittle wrappers around subscription CLIs + systemd + worktrees: auth can
# expire, timers can drift, worktrees can stick, disk can fill — all silently. This checks each and
# logs any rot to the ops truth ledger (event=failed), so the morning digest's 🔴 fires + the bot's
# system-state surfaces it. Lightweight (no live model call). $0. Run every few hours via systemd.
# Kill: touch /opt/fpai-build/.health_disabled
set -uo pipefail
[ -f /opt/fpai-build/.health_disabled ] && exit 0
REPO_ROOT=${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}
OL=${OPS_LOG_SCRIPT:-$REPO_ROOT/tools/build_loop/ops_log.py}
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

# 7. expected-rate monitor + canary sanity for the answered-decision build loop.
# Skips on non-server sandboxes without a DB DSN; on 162, BRAIN_INDEX_DB_URL is expected.
while IFS=$'\t' read -r kind msg next; do
  [ "$kind" = "FAIL" ] && fail "$msg" "$next"
done < <(
  OPS_LEDGER_PATH="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}" python3 - <<'PY'
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
if not dsn:
    raise SystemExit(0)

try:
    import psycopg
except Exception as exc:
    print(f"FAIL\tbuild loop health DB check cannot import psycopg: {exc}\tEmber: run health_check.sh inside the curator/build venv")
    raise SystemExit(0)

repo = Path(os.environ.get("FPAI_REPO_ROOT", "/opt/fpai-build/FPAI_Cockpit"))
curator_root = repo / "SERVICES" / "sunheart-brain"
if str(curator_root) not in sys.path:
    sys.path.insert(0, str(curator_root))

try:
    from curator import decisions
except Exception as exc:
    print(f"FAIL\tbuild loop health cannot import curator.decisions: {exc}\tEmber: deploy the d027 curator decision module")
    raise SystemExit(0)


def ts(value):
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def last_successful_build(path):
    best = None
    if not path.exists():
        return None
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            try:
                row = json.loads(raw)
            except Exception:
                continue
            if row.get("event") != "loop_run":
                continue
            try:
                built = int(row.get("built") or 0)
            except (TypeError, ValueError):
                built = 0
            if built <= 0:
                continue
            seen = ts(row.get("ts"))
            if seen and (best is None or seen > best):
                best = seen
    return best


try:
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)::int
                  FROM brain_index.decisions
                 WHERE COALESCE(needs_build, false) = true
                   AND COALESCE(spec_written, false) = false
                   AND COALESCE(is_canary, false) = false
                """
            )
            pending_count = int(cur.fetchone()[0])
            cur.execute(
                """
                SELECT EXISTS(
                    SELECT 1 FROM brain_index.decisions
                     WHERE id = 'd000'
                       AND COALESCE(is_canary, false) = true
                       AND COALESCE(needs_build, false) = true
                       AND COALESCE(spec_written, false) = false
                )
                """
            )
            canary_exists = bool(cur.fetchone()[0])
        pending_via_api = len(decisions.pending_builds(conn))
except Exception as exc:
    print(f"FAIL\tbuild loop health DB check failed: {exc}\tEmber: verify BRAIN_INDEX_DB_URL, migration d027, and curator.decisions on 162")
    raise SystemExit(0)

last = last_successful_build(Path(os.environ["OPS_LEDGER_PATH"]))
if pending_count > 0:
    if last is None:
        print(
            f"FAIL\tbuild loop has {pending_count} decisions pending but no successful build in never — possible DB/env gap"
            "\tEmber: check bridge_to_codex.sh, ops_ledger loop_run rows, and build-loop service env"
        )
    else:
        age_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        if age_h > 2:
            print(
                f"FAIL\tbuild loop has {pending_count} decisions pending but no successful build in {age_h:.1f}h — possible DB/env gap"
                "\tEmber: check bridge_to_codex.sh, ops_ledger loop_run rows, and build-loop service env"
            )

if canary_exists and pending_count > 0 and pending_via_api == 0:
    print(
        f"FAIL\tpending_builds() returned 0 but DB shows {pending_count} real pending — DB connection or query broken"
        "\tEmber: inspect curator.decisions pending-builds query and BRAIN_INDEX_DB_URL"
    )
PY
)

echo "health check done $(date -u +%H:%M)Z"
