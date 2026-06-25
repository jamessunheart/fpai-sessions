#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$ROOT/tools/forge/auto_merge.sh"
TMPDIR="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

check() {
  local desc="$1" exp="$2" act="$3" needle="$4" output="$5"
  if [ "$exp" = "$act" ] && printf '%s' "$output" | grep -q "$needle"; then
    echo "  ✓ $desc"; PASS=$((PASS+1))
  else
    echo "  ✗ $desc (exit exp=$exp act=$act; wanted '$needle')"
    printf '%s\n' "$output" | sed 's/^/      /'
    FAIL=$((FAIL+1))
  fi
}

make_repo() {
  local name="$1"
  local repo="$TMPDIR/$name"
  mkdir -p "$repo/core/BUILD" "$repo/tools/build_loop"
  git -C "$repo" init -q -b main
  git -C "$repo" config user.email "test@example.invalid"
  git -C "$repo" config user.name "Auto Merge Test"
  printf 'base\n' > "$repo/README.md"
  git -C "$repo" add README.md
  git -C "$repo" commit -q -m "base"
  git -C "$repo" update-ref refs/remotes/origin/main HEAD
  cat > "$repo/tools/build_loop/ops_log.py" <<'PY'
#!/usr/bin/env python3
import json, os, sys
row = {"loop": sys.argv[1], "event": sys.argv[2], "detail": sys.argv[3] if len(sys.argv) > 3 else ""}
with open(os.environ["OPS_LEDGER"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(row) + "\n")
PY
  chmod +x "$repo/tools/build_loop/ops_log.py"
  printf '%s\n' "$repo"
}

write_registry() {
  local repo="$1" branch="$2" risk="$3" approved="$4"
  python3 - "$repo/core/BUILD/REGISTRY.json" "$branch" "$risk" "$approved" <<'PY'
import json, sys
path, branch, risk, approved = sys.argv[1:5]
data = {
  "schema": "build-registry.v1",
  "updated_at": "2026-06-17T00:00:00Z",
  "active_builds": [{
    "id": branch.replace("/", "-"),
    "slug": branch.replace("/", "-"),
    "branch": branch,
    "status": "done",
    "tests_passed": True,
    "risk": risk,
    "ai_approved": approved == "true",
    "ai_review": {"verdict": "APPROVE" if approved == "true" else "REQUEST_CHANGES", "risk": risk},
  }],
}
open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2) + "\n")
PY
}

make_notify() {
  local path="$1"
  cat > "$path" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$1" >> "$NOTIFY_OUT"
SH
  chmod +x "$path"
}

echo "auto_merge tests"

# T1: approved low-risk doc-only branch merges and logs.
repo="$(make_repo doc_only)"
git -C "$repo" checkout -q -b build/doc-only
mkdir -p "$repo/docs"
printf 'doc\n' > "$repo/docs/note.md"
git -C "$repo" add docs/note.md
git -C "$repo" commit -q -m "doc only"
git -C "$repo" checkout -q main
write_registry "$repo" "build/doc-only" "low" "true"
notify="$TMPDIR/notify-doc.sh"; make_notify "$notify"
ledger="$TMPDIR/doc-ledger.jsonl"; notify_out="$TMPDIR/doc-notify.txt"
OUT=$(FPAI_REPO_ROOT="$repo" AUTO_MERGE_REGISTRY="$repo/core/BUILD/REGISTRY.json" OPS_LEDGER="$ledger" NOTIFY_SCRIPT="$notify" NOTIFY_OUT="$notify_out" bash "$SCRIPT" "build/doc-only" 2>&1); RC=$?
check "doc-only approved low risk -> merge" 0 "$RC" "AUTO-MERGED" "$OUT"
if git -C "$repo" rev-parse --verify HEAD:docs/note.md >/dev/null 2>&1 && grep -q '"event": "merged"' "$ledger"; then
  echo "  ✓ merge produced doc and ops ledger row"; PASS=$((PASS+1))
else
  echo "  ✗ merge produced doc and ops ledger row"; FAIL=$((FAIL+1))
fi

# T2: code-like file is held and not merged.
repo="$(make_repo code_file)"
git -C "$repo" checkout -q -b build/code-file
mkdir -p "$repo/tools"
printf 'print("x")\n' > "$repo/tools/x.py"
git -C "$repo" add tools/x.py
git -C "$repo" commit -q -m "code"
git -C "$repo" checkout -q main
write_registry "$repo" "build/code-file" "low" "true"
notify="$TMPDIR/notify-code.sh"; make_notify "$notify"
ledger="$TMPDIR/code-ledger.jsonl"; notify_out="$TMPDIR/code-notify.txt"
OUT=$(FPAI_REPO_ROOT="$repo" AUTO_MERGE_REGISTRY="$repo/core/BUILD/REGISTRY.json" OPS_LEDGER="$ledger" NOTIFY_SCRIPT="$notify" NOTIFY_OUT="$notify_out" bash "$SCRIPT" "build/code-file" 2>&1); RC=$?
check "code file -> held" 1 "$RC" "code-like files present" "$OUT"
if ! git -C "$repo" rev-parse --verify HEAD:tools/x.py >/dev/null 2>&1 && grep -q 'merge build-code-file' "$notify_out"; then
  echo "  ✓ code hold avoided merge and notified"; PASS=$((PASS+1))
else
  echo "  ✗ code hold avoided merge and notified"; FAIL=$((FAIL+1))
fi

# T3: approved but non-low risk is held.
repo="$(make_repo med_risk)"
git -C "$repo" checkout -q -b build/med-risk
mkdir -p "$repo/docs"
printf 'doc\n' > "$repo/docs/risk.md"
git -C "$repo" add docs/risk.md
git -C "$repo" commit -q -m "doc med risk"
git -C "$repo" checkout -q main
write_registry "$repo" "build/med-risk" "med" "true"
notify="$TMPDIR/notify-risk.sh"; make_notify "$notify"
ledger="$TMPDIR/risk-ledger.jsonl"; notify_out="$TMPDIR/risk-notify.txt"
OUT=$(FPAI_REPO_ROOT="$repo" AUTO_MERGE_REGISTRY="$repo/core/BUILD/REGISTRY.json" OPS_LEDGER="$ledger" NOTIFY_SCRIPT="$notify" NOTIFY_OUT="$notify_out" bash "$SCRIPT" "build/med-risk" 2>&1); RC=$?
check "non-low risk -> held" 1 "$RC" "risk is not low" "$OUT"

echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
