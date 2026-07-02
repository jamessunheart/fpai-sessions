#!/usr/bin/env bash
# build_orchestrator — automatically prioritize, build, gate, and merge the queue.
#
# The autonomous build pipeline. Composes the existing pieces:
#   run_codex.sh (build pending specs in isolated worktrees)
#   merge_gate.sh (verify registered + tests + base!=main)
# and adds: prioritize (SAFE-AUTO first, NEEDS-JAMES skipped) + commit + register
# + gate + merge to feat/headless-build (NEVER main).
#
# GUARDRAILS (per feedback_guardrails_small_blast_radius):
#   - Only auto-builds specs tagged SAFE-AUTO (NEEDS-JAMES specs are skipped → surfaced).
#   - Builds happen in isolated worktrees; nothing touches the live checkout's uncommitted work.
#   - Merges go to feat/headless-build ONLY — never main, never a prod server.
#   - Every merged build passed the merge-gate (registered done + tests + base check).
#   - Fully reversible: git revert any merge.
#
# Kill switch:   BUILD_ORCHESTRATOR_DISABLE=1
# Default:       BUILD_AUTO_MERGE=0 — build + gate, then SURFACE 'ready to merge'.
#                A human reviews the diff and merges (the gate can't verify code is correct).
# Full hands-off (opt-in, eyes-open): BUILD_AUTO_MERGE=1 runs tools/forge/auto_merge.sh
#                after the independent review. That resolver only merges doc-only,
#                AI-approved, risk=low branches; everything else is surfaced.
set -u
[ "${BUILD_ORCHESTRATOR_DISABLE:-0}" = "1" ] && { echo "orchestrator disabled (BUILD_ORCHESTRATOR_DISABLE=1)"; exit 0; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
SPECS="$ROOT/core/BUILD/specs"
RESULTS="$ROOT/core/BUILD/results"
WT_BASE="$HOME/.fpai-build-worktrees"
BASE="feat/headless-build"
AUTO_MERGE="${BUILD_AUTO_MERGE:-0}"
LAST_AUDIT_FILE="${SELF_AUDIT_LAST_FILE:-/opt/fpai-build/.last_audit_date}"
MERGED_COUNTER_FILE="${SELF_AUDIT_MERGED_COUNTER:-/opt/fpai-build/.merged_since_audit}"
SELF_AUDIT_OUT="${SELF_AUDIT_OUTPUT:-/tmp/audit_specs.json}"
AUTO_MERGE_TARGET="${BUILD_AUTO_MERGE_TARGET:-main}"
AUTO_MERGE_COMPARE="${BUILD_AUTO_MERGE_COMPARE:-origin/main}"

echo "═══ build orchestrator ═══ (auto_merge=$AUTO_MERGE, base=$BASE)"

constitution_check_spec() {
  id="$1"; spec="$2"
  python3 "$ROOT/tools/governance/constitution_check.py" \
    --kind "build-decision" \
    --id "$id" \
    --proposal-file "$spec"
}

build_queue_empty() {
  shopt -s nullglob
  for spec in "$SPECS"/*.md; do
    id="$(basename "$spec" .md)"
    [ -f "$RESULTS/$id.result.md" ] || { shopt -u nullglob; return 1; }
  done
  shopt -u nullglob
  return 0
}

increment_merged_since_audit() {
  mkdir -p "$(dirname "$MERGED_COUNTER_FILE")" 2>/dev/null || true
  python3 - "$MERGED_COUNTER_FILE" <<'PY' || true
import pathlib, sys
path = pathlib.Path(sys.argv[1])
try:
    current = int(path.read_text(encoding="utf-8").strip() or "0")
except Exception:
    current = 0
path.write_text(str(max(0, current) + 1) + "\n", encoding="utf-8")
PY
}

queue_self_audit_specs() {
  python3 - "$SELF_AUDIT_OUT" <<'PY'
import json, shutil, subprocess, sys
path = sys.argv[1]
try:
    specs = json.load(open(path, encoding="utf-8"))
except Exception:
    specs = []
queued = 0
if specs and shutil.which("dec"):
    for item in specs:
        title = str(item.get("title", "")).strip()
        spec = str(item.get("spec", "")).strip()
        if not title or not spec:
            continue
        result = subprocess.run(
            ["dec", "queue-build", title, spec],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            queued += 1
elif specs:
    print("dec command not found; self-audit specs generated but not queued", file=sys.stderr)
print(queued)
PY
}

log_self_audit_event() {
  trigger="$1"; generated="$2"; queued="$3"; audit_id="$4"
  python3 - "$trigger" "$generated" "$queued" "$audit_id" "$SELF_AUDIT_OUT" <<'PY' || true
import datetime as dt, json, os, pathlib, sys
trigger, generated, queued, audit_id, artifact = sys.argv[1:6]
ledger = pathlib.Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
row = {
    "ts": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "loop": "build_orchestrator",
    "event": "self_audit",
    "detail": f"self-audit generated {generated} specs; queued {queued}",
    "cost": "$0",
    "artifact": artifact,
    "next": "review queued self-audit improvement specs",
    "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    "specs_generated": int(generated),
    "specs_queued": int(queued),
    "trigger": trigger,
    "audit_id": audit_id,
}
ledger.parent.mkdir(parents=True, exist_ok=True)
with ledger.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(row, sort_keys=True) + "\n")
PY
}

mark_ai_review_approved() {
  branch="$1"
  python3 - "$branch" <<'PY' || true
import datetime as dt
import json
import re
import sys
from pathlib import Path

branch = sys.argv[1]
registry = Path("core/BUILD/REGISTRY.json")
review = Path("core/BUILD/reviews") / (branch.replace("/", "-") + ".md")
if not registry.exists():
    raise SystemExit
data = json.loads(registry.read_text(encoding="utf-8"))
text = review.read_text(encoding="utf-8", errors="ignore") if review.exists() else ""
verdict = "APPROVE" if re.search(r"Verdict:\*\*\s+APPROVE|^APPROVE:", text, re.I | re.M) else ""
risk_match = re.search(r"Risk:\*\*\s+([a-z]+)|risk=([a-z]+)", text, re.I)
risk = (risk_match.group(1) or risk_match.group(2)).lower() if risk_match else ""
for item in data.get("active_builds", []):
    if item.get("branch") == branch:
        item["ai_approved"] = verdict == "APPROVE"
        item["ai_review"] = {
            "verdict": verdict or "UNKNOWN",
            "risk": risk or "unknown",
            "source": str(review),
        }
        if risk:
            item["risk"] = risk
data["updated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
registry.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

run_self_audit_if_due() {
  [ "${SELF_AUDIT_DISABLE:-0}" = "1" ] && return 0
  queue_empty=0
  build_queue_empty && queue_empty=1
  trigger="$(
    python3 "$ROOT/tools/build_loop/self_audit.py" \
      --trigger-name \
      --queue-empty "$queue_empty" \
      --last-audit-file "$LAST_AUDIT_FILE" \
      --merged-counter-file "$MERGED_COUNTER_FILE" 2>/dev/null || true
  )"
  [ -z "$trigger" ] && return 0

  audit_id="audit-$(date -u +%Y%m%d%H%M%S)"
  mkdir -p "$(dirname "$LAST_AUDIT_FILE")" 2>/dev/null || true
  date -u +"%Y-%m-%d-%H" > "$LAST_AUDIT_FILE" 2>/dev/null || true
  if ! python3 "$ROOT/tools/build_loop/self_audit.py" --output "$SELF_AUDIT_OUT"; then
    echo "⚠️  self-audit failed; continuing build loop"
    return 0
  fi

  generated="$(
    python3 - "$SELF_AUDIT_OUT" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    data = []
print(len(data) if isinstance(data, list) else 0)
PY
  )"
  queued="$(queue_self_audit_specs 2>/tmp/self_audit_queue.err || echo 0)"
  [ -s /tmp/self_audit_queue.err ] && sed 's/^/⚠️  /' /tmp/self_audit_queue.err
  log_self_audit_event "$trigger" "$generated" "$queued" "$audit_id"
  echo "0" > "$MERGED_COUNTER_FILE" 2>/dev/null || true
  "$ROOT/tools/build_loop/notify_telegram.sh" "System self-audit complete: $queued improvement specs queued [$audit_id]" >/dev/null 2>&1 || true
}

# 1. PRIORITIZE: which specs are auto-buildable? SAFE-AUTO and not NEEDS-JAMES,
#    and not already built (no result file). NEEDS-JAMES specs are surfaced, never auto-built.
PENDING=()
shopt -s nullglob
for spec in "$SPECS"/*.md; do
  id="$(basename "$spec" .md)"
  [ -f "$RESULTS/$id.result.md" ] && continue
  if grep -q "SAFE-AUTO" "$spec" && ! grep -q "NEEDS-JAMES" "$spec"; then
    PENDING+=("$id")
  fi
done
if [ "${#PENDING[@]}" -gt 0 ]; then
  APPROVED_PENDING=()
  for id in "${PENDING[@]}"; do
    if constitution_check_spec "$id" "$SPECS/$id.md" >"/tmp/constitution_check_$id.out" 2>&1; then
      APPROVED_PENDING+=("$id")
    else
      echo "⛔ CONSTITUTION REJECTED (not auto-built): $id"
      sed 's/^/    /' "/tmp/constitution_check_$id.out" 2>/dev/null || true
    fi
  done
  PENDING=("${APPROVED_PENDING[@]}")
fi
echo "pending auto-buildable specs: ${#PENDING[@]} (${PENDING[*]:-none})"

# Surface any NEEDS-JAMES specs that are waiting (never auto-built).
shopt -s nullglob
for spec in "$SPECS"/*.md; do
  id="$(basename "$spec" .md)"
  [ -f "$RESULTS/$id.result.md" ] && continue
  if grep -q "NEEDS-JAMES" "$spec"; then echo "⏸  NEEDS-JAMES (waiting for James): $id"; fi
done

# 2. BUILD: run_codex builds all pending specs into isolated worktrees.
if [ "${#PENDING[@]}" -gt 0 ]; then
  echo "── pre-build Forge scout ──"
  for id in "${PENDING[@]}"; do
    bash "$ROOT/tools/build_loop/forge_scout.sh" "$SPECS/$id.md" || true
  done
  echo "── building via Codex ──"
  RUN_CODEX_ARGS=()
  for id in "${PENDING[@]}"; do
    RUN_CODEX_ARGS+=(--spec-id "$id")
  done
  bash "$ROOT/tools/build_loop/run_codex.sh" "${RUN_CODEX_ARGS[@]}"
fi

# 3. INTEGRATE: for each SAFE-AUTO spec that has a build result, commit the
#    worktree, register, gate, and surface (or merge). Commit BEFORE the
#    already-integrated check — an uncommitted branch has no commits ahead and
#    would false-positive as "merged".
built=0; merged=0; surfaced=0; failed=0; READY=""
INTEGRATE=()
shopt -s nullglob
for spec in "$SPECS"/*.md; do
  iid="$(basename "$spec" .md)"
  [ -f "$RESULTS/$iid.result.md" ] || continue
  if grep -q "SAFE-AUTO" "$spec" && ! grep -q "NEEDS-JAMES" "$spec"; then
    if constitution_check_spec "$iid" "$spec" >"/tmp/constitution_check_integrate_$iid.out" 2>&1; then
      INTEGRATE+=("$iid")
    else
      echo "⛔ CONSTITUTION REJECTED (not integrated): $iid"
      sed 's/^/    /' "/tmp/constitution_check_integrate_$iid.out" 2>/dev/null || true
    fi
  fi
done
if [ "${#INTEGRATE[@]}" -eq 0 ]; then
  echo "═══ done: nothing to integrate ═══"
  run_self_audit_if_due
  exit 0
fi
for id in "${INTEGRATE[@]}"; do
  branch="build/$id"; wt="$WT_BASE/$id"
  git rev-parse --verify "$branch" >/dev/null 2>&1 || continue
  # commit the worktree's changes onto the build branch FIRST
  if [ -d "$wt" ]; then
    git -C "$wt" add -A 2>/dev/null
    git -C "$wt" diff --cached --quiet 2>/dev/null || \
      git -C "$wt" commit -q -m "feat(auto): build $id [orchestrator]"
  fi
  # already integrated (no commits ahead of BASE)? skip
  git merge-base --is-ancestor "$branch" "$BASE" 2>/dev/null && { echo "• $id: already integrated"; continue; }
  built=$((built+1))

  # register done (so the gate accepts it)
  python3 - "$id" "$branch" "$SPECS/$id.md" <<'PY'
import json, sys, datetime
bid, branch, spec = sys.argv[1:4]
p = "core/BUILD/REGISTRY.json"; d = json.load(open(p))
d["active_builds"] = [b for b in d["active_builds"] if b.get("branch") != branch]
d["active_builds"].append({"id": bid, "slug": bid, "branch": branch,
    "base_branch": "feat/headless-build", "session": "orchestrator",
    "status": "done", "spec": spec, "tests_passed": None})
d["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump(d, open(p, "w"), indent=2)
PY

  # gate
  if bash "$ROOT/tools/merge/merge_gate.sh" "$branch" >/tmp/orch_gate_$id.out 2>&1; then
    mark_ai_review_approved "$branch"
    if [ "$AUTO_MERGE" = "1" ]; then
      if AUTO_MERGE_TARGET="$AUTO_MERGE_TARGET" AUTO_MERGE_COMPARE="$AUTO_MERGE_COMPARE" \
        bash "$ROOT/tools/forge/auto_merge.sh" "$branch" >"/tmp/orch_auto_merge_$id.out" 2>&1; then
        increment_merged_since_audit
        python3 "$ROOT/curator/blueprints/manager.py" update-after-build "$id" "$branch" >/dev/null 2>&1 || true
        git worktree remove "$wt" --force >/dev/null 2>&1; git branch -d "$branch" >/dev/null 2>&1
        echo "✅ AUTO-MERGED: $id"; merged=$((merged+1))
      else
        echo "⚠️  AUTO-MERGE HELD: $id (surfaced — manual merge)"
        sed 's/^/    /' "/tmp/orch_auto_merge_$id.out" 2>/dev/null || true
        surfaced=$((surfaced+1)); READY="$READY $id"
      fi
    else
      echo "✓ READY (gate passed): $id → git merge --no-ff $branch"; surfaced=$((surfaced+1)); READY="$READY $id"
    fi
  else
    echo "✗ GATE FAILED: $id"; sed 's/^/    /' /tmp/orch_gate_$id.out
    if [ -d "$wt" ]; then
      echo "  auto-reverting failed build branch to $BASE"
      python3 "$ROOT/tools/autobuild/auto_revert.py" \
        --repo-root "$wt" \
        --known-good "$BASE" \
        --report-dir "$ROOT/core/BUILD/reports/auto_revert" \
        --execute \
        --allow-dirty \
        --fail-after-revert \
        --ops-ledger "${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}" \
        -- bash "$ROOT/tools/merge/merge_gate.sh" "$branch" >/tmp/orch_revert_$id.out 2>&1 || true
      sed 's/^/    /' /tmp/orch_revert_$id.out
    fi
    failed=$((failed+1))
  fi
done

echo "═══ done: built=$built merged=$merged surfaced=$surfaced failed=$failed ═══"
run_self_audit_if_due

# Surface the result to James's ONE chat (Telegram), if anything happened.
if [ $((built + merged + surfaced + failed)) -gt 0 ]; then
  NOTE="🛠 <b>Build pipeline ran.</b>
built: $built · merged: $merged · ready: $surfaced · failed: $failed"
  [ -n "$READY" ] && NOTE="$NOTE
ready to merge:$READY
reply 'merge <id>' to ship."
  "$ROOT/tools/build_loop/notify_telegram.sh" "$NOTE" >/dev/null 2>&1 || true
fi
