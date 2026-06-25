#!/usr/bin/env bash
# auto_merge — merge only doc-only, independently approved, low-risk builds.
#
# This is intentionally narrower than the merge gate. The gate proves a branch is
# registered, tested, and independently reviewed; this resolver decides whether
# the merge is boring enough to happen without a manual shell command.
#
# Usage:
#   tools/forge/auto_merge.sh <branch>
#
# Environment:
#   AUTO_MERGE_REGISTRY  registry path (default: core/BUILD/REGISTRY.json)
#   AUTO_MERGE_TARGET    target branch to merge into (default: main)
#   AUTO_MERGE_COMPARE   diff base for doc-only check (default: origin/main)
#   NOTIFY_SCRIPT        Telegram notifier (default: tools/build_loop/notify_telegram.sh)
#   OPS_LEDGER           ops ledger path (default: /opt/fpai-build/ops_ledger.jsonl)
set -u

BRANCH="${1:-}"
[ -z "$BRANCH" ] && { echo "usage: auto_merge.sh <branch>"; exit 2; }

ROOT="${FPAI_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
REG="${AUTO_MERGE_REGISTRY:-$ROOT/core/BUILD/REGISTRY.json}"
TARGET="${AUTO_MERGE_TARGET:-main}"
COMPARE="${AUTO_MERGE_COMPARE:-origin/main}"
NOTIFY="${NOTIFY_SCRIPT:-$ROOT/tools/build_loop/notify_telegram.sh}"
OPS_LOG="$ROOT/tools/build_loop/ops_log.py"

cd "$ROOT" || exit 2

log_ops() {
  local event="$1" detail="$2" artifact="${3:-}" next="${4:-}"
  if [ -f "$OPS_LOG" ]; then
    FPAI_SURFACE="${FPAI_SURFACE:-auto-merge}" OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}" \
      python3 "$OPS_LOG" "auto_merge" "$event" "$detail" '$0' "$artifact" "$next" >/dev/null 2>&1 || true
  fi
}

notify_james() {
  local title="$1" body="$2"
  [ -x "$NOTIFY" ] || return 0
  "$NOTIFY" "⚠️ <b>${title}</b>
${body}

Tap/reply: <code>merge ${BUILD_ID:-$BRANCH}</code>" >/dev/null 2>&1 || true
}

fail_prompt() {
  local reason="$1" detail="$2"
  echo "AUTO-MERGE HELD: $reason"
  [ -n "$detail" ] && echo "$detail"
  log_ops "failed" "$BRANCH held: $reason" "" "James review: merge ${BUILD_ID:-$BRANCH}"
  notify_james "Auto-merge held: ${BUILD_ID:-$BRANCH}" "$reason
<pre>${detail}</pre>"
  exit 1
}

if [ "$BRANCH" = "$TARGET" ] || [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  fail_prompt "refusing to merge target/main branch" "$BRANCH"
fi

if ! git rev-parse --verify "$BRANCH" >/dev/null 2>&1 && \
   ! git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
  fail_prompt "branch not found" "$BRANCH"
fi

if ! git rev-parse --verify "$TARGET" >/dev/null 2>&1; then
  fail_prompt "target branch not found" "$TARGET"
fi

if ! git rev-parse --verify "$COMPARE" >/dev/null 2>&1; then
  fail_prompt "compare ref not found" "$COMPARE"
fi

META="$(
  python3 - "$REG" "$BRANCH" <<'PY'
import json, shlex, sys
from pathlib import Path

path = Path(sys.argv[1])
branch = sys.argv[2]
if not path.exists():
    print("FOUND=0")
    raise SystemExit

data = json.loads(path.read_text(encoding="utf-8"))
items = data.get("active_builds", [])
entry = next((item for item in items if item.get("branch") == branch), None)
if entry is None and branch.startswith("origin/"):
    entry = next((item for item in items if "origin/" + str(item.get("branch", "")) == branch), None)
if entry is None:
    print("FOUND=0")
    raise SystemExit

review = entry.get("ai_review") if isinstance(entry.get("ai_review"), dict) else {}
verdict = str(review.get("verdict") or entry.get("ai_review_verdict") or "").upper()
risk = str(review.get("risk") or entry.get("risk") or entry.get("risk_class") or "").lower()
approved = entry.get("ai_approved") is True or verdict == "APPROVE"
print("FOUND=1")
print("BUILD_ID=" + shlex.quote(str(entry.get("id") or entry.get("slug") or branch)))
print("STATUS=" + shlex.quote(str(entry.get("status") or "")))
print("RISK=" + shlex.quote(risk))
print("AI_APPROVED=" + ("1" if approved else "0"))
PY
)"
eval "$META"

[ "${FOUND:-0}" = "1" ] || fail_prompt "branch is not registered" "$BRANCH"
[ "${STATUS:-}" = "done" ] || fail_prompt "registry status is not done" "status=${STATUS:-missing}"
[ "${AI_APPROVED:-0}" = "1" ] || fail_prompt "registry does not mark AI approval" "ai_approved=${AI_APPROVED:-0}"
[ "${RISK:-}" = "low" ] || fail_prompt "registry risk is not low" "risk=${RISK:-missing}"

CHANGED="$(git diff --name-only "$COMPARE...$BRANCH" 2>/dev/null || true)"
[ -n "$CHANGED" ] || fail_prompt "no diff to merge" "$COMPARE...$BRANCH"

CODE_FILES="$(
  printf '%s\n' "$CHANGED" | awk '
    /\.py$/ || /\.sh$/ || /\.sql$/ || /\.env$/ || /(^|\/)\.env($|[.\/])/ { print }
  '
)"
if [ -n "$CODE_FILES" ]; then
  fail_prompt "code-like files present; manual merge required" "$CODE_FILES"
fi

CURRENT="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [ "$CURRENT" != "$TARGET" ]; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    fail_prompt "working tree is dirty; cannot switch to target" "$(git status --short)"
  fi
  git checkout "$TARGET" >/dev/null 2>&1 || fail_prompt "could not checkout target branch" "$TARGET"
fi

MERGE_OUT="$(mktemp)"
if git merge --no-edit "$BRANCH" >"$MERGE_OUT" 2>&1; then
  python3 - "$REG" "$BRANCH" <<'PY' || true
import datetime as dt, json, sys
from pathlib import Path

path = Path(sys.argv[1])
branch = sys.argv[2]
if not path.exists():
    raise SystemExit
data = json.loads(path.read_text(encoding="utf-8"))
for item in data.get("active_builds", []):
    if item.get("branch") == branch:
        item["status"] = "merged"
        item["merged_by"] = "auto_merge"
        item["merged_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
data["updated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
  log_ops "merged" "$BUILD_ID auto-merged into $TARGET" "$REG" "James can veto by reverting the merge commit"
  [ -x "$NOTIFY" ] && "$NOTIFY" "✅ <b>Auto-merged:</b> ${BUILD_ID}
target: <code>${TARGET}</code>
doc-only diff; AI-approved; risk=low.
Veto path: revert the merge commit." >/dev/null 2>&1 || true
  echo "AUTO-MERGED: $BUILD_ID -> $TARGET"
  rm -f "$MERGE_OUT"
  exit 0
fi

RC=$?
DETAIL="$(cat "$MERGE_OUT" 2>/dev/null)"
rm -f "$MERGE_OUT"
git merge --abort >/dev/null 2>&1 || true
fail_prompt "merge exited $RC; conflict/manual merge required" "$DETAIL"
