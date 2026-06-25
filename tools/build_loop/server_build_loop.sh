#!/usr/bin/env bash
# server_build_loop.sh — laptop-FREE autonomous build runner. Runs ON server 162 via a
# systemd timer. For each answered+needs_build decision: builds with Codex in an isolated
# worktree off feat/headless-build ($0 ChatGPT Max), commits it, reviews with claude -p
# ($0 Claude Max, via tools/merge/ai_review.py — PROTECTED_PATHS aware), records the result
# on the decision, and surfaces the verdict to James's Telegram.
# Both build + review are subscription = $0 marginal. Runs until queue empty.
#
# Smart gates (not arbitrary count caps — builds are $0):
#   CONSECUTIVE_REVERTS_MAX: halt if N builds in a row auto-revert (broken specs signal)
#   DISK_WARN_GB: warn+continue if worktrees > N GB; halt at 2x
#   BUILD_MAX: max builds per single timer run (prevents one run hogging the slot)
# Kill: touch /opt/fpai-build/.disabled
set -uo pipefail
REPO=/opt/fpai-build/FPAI_Cockpit
WT_BASE=/opt/fpai-build/worktrees
BASE=feat/headless-build
BRAIN=/opt/sh-brain-src
PY="$BRAIN/.venv/bin/python"
BUILD_MAX="${BUILD_MAX:-5}"
CONSECUTIVE_REVERTS_MAX="${CONSECUTIVE_REVERTS_MAX:-3}"
DISK_WARN_GB="${DISK_WARN_GB:-30}"
STAMP=/opt/fpai-build/.daily_count
DISABLED=/opt/fpai-build/.disabled
DRY="${1:-}"

[ -f "$DISABLED" ] && { echo "server build loop DISABLED (flag present)"; exit 0; }
[ "$DRY" = "--dry-run" ] && { echo "DRY RUN — no changes will be made"; }

# env: bot env (DB + telegram creds) + claude OAuth token (for the $0 review)
# Explicit export ensures subshells (Python) inherit these even when source fails mid-file
ENVFILE=$(systemctl show sh-brain-tgbot -p EnvironmentFiles 2>/dev/null | sed -E 's/EnvironmentFiles=//; s/ .*//')
set -a; . "$ENVFILE" 2>/dev/null; . /root/.config/fpai/claude.env 2>/dev/null; set +a
# Belt-and-suspenders: explicitly export DB URL so psycopg subshells see it
# (curator.env has a multi-word value that breaks mid-file source in some bash versions)
[ -z "${BRAIN_INDEX_DB_URL:-}" ] && export BRAIN_INDEX_DB_URL=$(grep "^BRAIN_INDEX_DB_URL=" /etc/sh-brain/curator.env | cut -d= -f2-)
export PATH="/root/.local/bin:$PATH"
mkdir -p "$WT_BASE"

# disk gate: warn at DISK_WARN_GB, halt at 2x
WT_GB=$(du -sg "$WT_BASE" 2>/dev/null | awk '{print $1}')
DISK_HALT_GB=$((DISK_WARN_GB * 2))
if [ "${WT_GB:-0}" -ge "$DISK_HALT_GB" ]; then
  tg "🔴 BUILD LOOP HALTED — worktrees using ${WT_GB}GB (limit ${DISK_HALT_GB}GB). Run reap_worktrees.sh to free space." 2>/dev/null || true
  echo "disk halt: ${WT_GB}GB worktrees >= ${DISK_HALT_GB}GB limit"; exit 1
fi

# informational daily count (no longer a gate — just telemetry)
TODAY=$(date -u +%Y-%m-%d)
CDATE="$TODAY"; CNUM=0
[ -f "$STAMP" ] && read -r CDATE CNUM < "$STAMP"
[ "$CDATE" != "$TODAY" ] && { CDATE="$TODAY"; CNUM=0; }
CONSECUTIVE_REVERTS=0

tg()  { ( cd "$BRAIN" && "$PY" -c "import asyncio,sys;from curator.telegram import send;asyncio.run(send(sys.argv[1]))" "$1" 2>/dev/null ) || true; }
dec() { ( cd "$BRAIN" && "$PY" -m curator.decisions "$@" 2>/dev/null ); }

review_file_for_branch() {
  local branch="$1"
  printf '%s/core/BUILD/reviews/%s.md' "$REPO" "${branch//\//-}"
}

review_findings() {
  local review_file="$1"
  if [ -f "$review_file" ]; then
    awk '
      /^## Findings[[:space:]]*$/ { in_findings=1; next }
      in_findings && /^## / { exit }
      in_findings && /^\*Reviewer:/ { exit }
      in_findings { print }
    ' "$review_file" | sed -n '1,120p'
  fi
}

run_revision_agent_attempt() {
  local attempt="$1"
  local review_file="$2"
  local feedback prompt status

  feedback="$(review_findings "$review_file")"
  if [ -z "$(printf '%s' "$feedback" | tr -d '[:space:]')" ]; then
    feedback="${REVIEW:-}"
  fi

  prompt="$(cat <<EOF
You are the revision agent for an already-built server build-loop branch.

Fix ONLY the specific issues flagged by the independent reviewer. Keep the same branch and worktree. Do not broaden scope, refactor unrelated code, add unrelated features, deploy, push, merge, touch secrets, send outreach, or move money.

Original spec:
$SPEC

Reviewer feedback:
$feedback

Revision constraints:
- Make the smallest code/test/doc changes needed to address the reviewer findings.
- Preserve the original spec intent.
- Run focused verification if feasible and mention it in any touched handoff/result note.
- Leave unrelated files and formatting alone.
EOF
)"

  codex exec --cd "$WT" --full-auto - <<<"$prompt" > "/opt/fpai-build/logs/$SPECID.revision-$attempt.codex.log" 2>&1
  status=$?
  python3 "$REPO/tools/build_loop/ops_log.py" revision attempted "$SPECID attempt=$attempt codex_rc=$status" "\$0" "$BR" "" 2>/dev/null || true

  if [ -n "$(git -C "$WT" status --porcelain)" ]; then
    git -C "$WT" add -A
    git -C "$WT" -c user.email=ember@fpai -c user.name=Ember commit -q -m "build($SPECID): revision agent pass $attempt"
    python3 "$REPO/tools/build_loop/ops_log.py" revision committed "$SPECID attempt=$attempt" "\$0" "$BR" "" 2>/dev/null || true
  else
    python3 "$REPO/tools/build_loop/ops_log.py" revision no-changes "$SPECID attempt=$attempt" "\$0" "$BR" "Ember: inspect unchanged flagged build" 2>/dev/null || true
  fi
}

queue_liveness_followup() {
  local log_file="$1"
  SPECID="$SPECID" DID="$DID" BR="$BR" LIVENESS_LOG_FILE="$log_file" "$PY" - <<'PY' | dec seed >/dev/null 2>&1 || true
import json
import os

specid = os.environ.get("SPECID", "")
did = os.environ.get("DID", "")
branch = os.environ.get("BR", "")
log_file = os.environ.get("LIVENESS_LOG_FILE", "")
print(json.dumps({
    "question": f"Liveness failed after auto-merge for {specid}",
    "build_spec": (
        f"Investigate and repair the post-merge liveness failure for {specid} "
        f"(decision {did}, branch {branch}). Start from the liveness log at {log_file}. "
        "Keep the fix scoped, reversible, tested, and do not deploy, push, merge, "
        "touch secrets, send outreach, or move money."
    ),
    "proof_expected": f"Liveness check for {specid} passes after the repair and ops_ledger records liveness:pass.",
}))
PY
}

run_liveness_probe() {
  local declaration="$1"
  local legacy_check="$2"
  local log_file status probe_status spec_file
  if [ "${LIVENESS_PROBE_DISABLE:-0}" = "1" ]; then
    python3 "$REPO/tools/build_loop/ops_log.py" liveness "liveness:skipped" "$SPECID disabled by LIVENESS_PROBE_DISABLE=1" "\$0" "$BR" "" 2>/dev/null || true
    return 0
  fi
  mkdir -p /opt/fpai-build/logs
  log_file="/opt/fpai-build/logs/$SPECID.liveness.log"
  spec_file="$REPO/core/BUILD/specs/$SPECID.md"
  (
    cd "$REPO" || exit 1
    export DID SPECID BR REPO WT BASE
    python3 -B -m tools.liveness.probe \
      --repo-root "$REPO" \
      --spec-file "$spec_file" \
      --declaration "$declaration" \
      --legacy-command "$legacy_check" \
      --spec-id "$SPECID" \
      --decision-id "$DID" \
      --branch "$BR"
  ) >"$log_file" 2>&1
  status=$?
  probe_status=$(tail -1 "$log_file" | "$PY" -c 'import json,sys; raw=sys.stdin.read().strip(); print((json.loads(raw).get("status") if raw else "") if raw else "")' 2>/dev/null || true)
  if [ "$status" = 0 ]; then
    return 0
  fi
  python3 "$REPO/tools/build_loop/ops_log.py" liveness "liveness:fail" "$SPECID status=${probe_status:-unknown} rc=$status log=$log_file" "\$0" "$BR" "Auto-queued follow-up repair spec for $DID" 2>/dev/null || true
  queue_liveness_followup "$log_file"
  return 0
}

"$PY" "$REPO/tools/build_loop/seed_orphaned_specs.py" --repo "$REPO" || true

# ── BACKLOG MERGE PASS ─────────────────────────────────────────────────────────
# Specs built before the auto-merge directive (2026-06-18) sit at build_status=
# 'changes' or 'built' with valid branches — never merged. Drain them 3/run so
# they don't flood one timer cycle. Same auto-merge policy as new builds.
MERGE_BACKLOG_MAX="${MERGE_BACKLOG_MAX:-3}"
BACKLOG_MERGED=0
# Also drain worktrees: branches checked out in linked worktrees that are ready to merge
WORKTREE_BRANCHES=$(git -C "$REPO" worktree list --porcelain 2>/dev/null | grep "branch refs/heads/build/" | sed 's|branch refs/heads/||')
BACKLOG_JSON=$("$PY" -c "
import psycopg, os, json
url = os.environ.get('BRAIN_INDEX_DB_URL','')
if not url: exit()
with psycopg.connect(url) as conn:
    rows = conn.execute('''
        SELECT id, build_branch FROM brain_index.decisions
        WHERE status=%s AND build_status = ANY(%s)
        AND build_branch IS NOT NULL AND build_branch != %s
        ORDER BY id
    ''', ('answered', ['changes','built'], '')).fetchall()
    for r in rows:
        print(json.dumps({'id': r[0], 'branch': r[1]}))
" 2>/dev/null || true)
# Add worktree branches not already in DB backlog
for WBR in $WORKTREE_BRANCHES; do
  echo "$BACKLOG_JSON" | grep -q "\"$WBR\"" || \
    BACKLOG_JSON="${BACKLOG_JSON}
$(printf '{"id":"%s","branch":"%s"}' "$(basename "$WBR" | grep -oE 'd[0-9]+'|head -1)" "$WBR")"
done

while IFS= read -r bline; do
  [ -z "$bline" ] && continue
  [ "$DRY" = "--dry-run" ] && { echo "  (dry-run) would merge: $bline"; continue; }
  [ "$BACKLOG_MERGED" -ge "$MERGE_BACKLOG_MAX" ] && { echo "backlog merge cap reached ($BACKLOG_MERGED/$MERGE_BACKLOG_MAX) — next run continues"; break; }
  BDID=$(printf '%s' "$bline"  | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])')
  BBR=$(printf '%s' "$bline"  | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["branch"])')
  # Skip if branch doesn't exist in repo
  git -C "$REPO" rev-parse --verify "$BBR" >/dev/null 2>&1 || { echo "backlog: branch $BBR gone, skipping $BDID"; continue; }
  echo "── backlog merge $BDID ($BBR) ──"
  git -C "$REPO" config user.email ember@fpai >/dev/null 2>&1; git -C "$REPO" config user.name Ember >/dev/null 2>&1
  git -C "$REPO" checkout "$BASE" >/dev/null 2>&1
  PRE_SHA=$(git -C "$REPO" rev-parse HEAD)
  BMERGED=0
  if git -C "$REPO" merge --no-edit "$BBR" >/dev/null 2>&1; then BMERGED=1
  else
    BU=$(git -C "$REPO" diff --name-only --diff-filter=U)
    if [ -n "$BU" ] && ! echo "$BU" | grep -qvE '^(core/BUILD/REGISTRY\.json|docs/codex/HANDOFF\.md|.*/__init__\.py)$'; then
      for f in $BU; do git -C "$REPO" checkout --ours "$f" >/dev/null 2>&1; done
      git -C "$REPO" add -A && git -C "$REPO" commit --no-edit >/dev/null 2>&1 && BMERGED=1
    else
      git -C "$REPO" merge --abort >/dev/null 2>&1
      echo "backlog: $BDID has real conflict — skip"
    fi
  fi
  if [ "$BMERGED" = 1 ]; then
    if ! "$PY" -c "import sys; sys.path.insert(0,'$BRAIN'); import curator, curator.decisions" >/dev/null 2>&1; then
      git -C "$REPO" reset --hard "$PRE_SHA" >/dev/null 2>&1
      tg "🔴 BACKLOG REVERT [$BDID] — import check failed. Branch $BBR held." 2>/dev/null || true
      echo "backlog: $BDID import check failed, reverted"
    else
      dec mark-merged "$BDID" >/dev/null 2>&1 || true
      BACKLOG_MERGED=$((BACKLOG_MERGED+1))
      python3 "$REPO/tools/build_loop/ops_log.py" merge backlog-merged "$BDID ($BBR)" "\$0" "$BBR" "" 2>/dev/null || true
      echo "backlog: merged $BDID"
    fi
  fi
done <<< "$BACKLOG_JSON"
[ "$BACKLOG_MERGED" -gt 0 ] && echo "backlog pass: merged $BACKLOG_MERGED specs"

PENDING=$(dec pending-builds | grep -E '^\{' || true)
[ -z "$PENDING" ] && { echo "no decisions awaiting a build"; exit 0; }
[ "$DRY" = "--dry-run" ] && { echo "PENDING BUILDS:"; printf '%s\n' "$PENDING"; exit 0; }

n=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  n=$((n+1)); [ "$n" -gt "$BUILD_MAX" ] && { echo "per-run cap reached ($n/$BUILD_MAX) — next run continues"; break; }

  DID=$(printf '%s' "$line"  | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])')
  SLUG=$(printf '%s' "$line" | "$PY" -c 'import sys,json,re;print(re.sub(r"[^a-z0-9]+","-",json.load(sys.stdin)["question"].lower())[:32].strip("-"))')
  LIVENESS_DECLARATION=$(printf '%s' "$line" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("liveness") or "")')
  LIVENESS_CHECK=$(printf '%s' "$line" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("liveness_check") or "")')
  SPECID="SPEC_${DID}_${SLUG}"; BR="build/$SPECID"; WT="$WT_BASE/$SPECID"
  echo "── building $SPECID (decision $DID) ──"

  SPEC=$(printf '%s' "$line" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
print(f"""# {d["id"]} — {d["question"][:60]}
Auto-generated by the server build loop from answered decision {d["id"]}.
## Build
{d.get("build_spec") or "(implement what the answer + proof_expected require)"}
## Context
- Question: {d["question"]}
- Answer: {d.get("answer","")}
- Proof expected: {d.get("proof_expected") or "(see answer)"}
## Contract
Follow docs/codex/SESSION_CONTRACT.md. Branch off feat/headless-build (never main).
Register in core/BUILD/REGISTRY.json. Tests required. Do NOT push or merge.
""")')

  # fresh isolated worktree off BASE
  git -C "$REPO" worktree remove --force "$WT" 2>/dev/null || true
  git -C "$REPO" branch -D "$BR" 2>/dev/null || true
  git -C "$REPO" worktree add -q -b "$BR" "$WT" "$BASE" || { echo "worktree add failed for $SPECID"; continue; }
  mkdir -p "$WT/core/BUILD/specs"; printf '%s\n' "$SPEC" > "$WT/core/BUILD/specs/$SPECID.md"

  # build ($0 codex) — log OUTSIDE the worktree so the transcript never lands in the build commit
  mkdir -p /opt/fpai-build/logs
  codex exec --cd "$WT" --full-auto - <<<"$SPEC" > "/opt/fpai-build/logs/$SPECID.codex.log" 2>&1 || echo "(codex exited non-zero — see /opt/fpai-build/logs/$SPECID.codex.log)"

  # commit the worktree (codex sandbox can't write git)
  if [ -n "$(git -C "$WT" status --porcelain)" ]; then
    git -C "$WT" add -A
    git -C "$WT" -c user.email=ember@fpai -c user.name=Ember commit -q -m "build($SPECID): server build loop"
  fi
  if ! git -C "$REPO" rev-parse --verify "$BR" >/dev/null 2>&1; then
    tg "⚠️ Build $SPECID produced no committable branch — held for manual review."
    python3 "$REPO/tools/build_loop/ops_log.py" build failed "$SPECID — codex produced no branch" "\$0" "" "Ember: manual review" 2>/dev/null || true
    continue
  fi

  # review ($0 claude -p, PROTECTED_PATHS aware)
  REVIEW=$(cd "$REPO" && "$PY" tools/merge/ai_review.py "$BR" 2>&1); RC=$?

  # Revision agent: flagged review gets up to 2 tightly-scoped same-branch repair passes
  # before falling back to the existing silent flagged auto-merge path. Protected-path
  # blocks (RC=2) stay hard stops.
  if [ "$RC" != 0 ] && [ "$RC" != 2 ]; then
    if [ "${REVISION_AGENT_DISABLE:-0}" = "1" ]; then
      python3 "$REPO/tools/build_loop/ops_log.py" revision skipped "$SPECID disabled by REVISION_AGENT_DISABLE=1" "\$0" "$BR" "" 2>/dev/null || true
    else
      REVISION_ATTEMPT=0
      while [ "$REVISION_ATTEMPT" -lt 2 ] && [ "$RC" != 0 ] && [ "$RC" != 2 ]; do
        REVISION_ATTEMPT=$((REVISION_ATTEMPT+1))
        REVIEW_FILE="$(review_file_for_branch "$BR")"
        run_revision_agent_attempt "$REVISION_ATTEMPT" "$REVIEW_FILE"
        REVIEW=$(cd "$REPO" && "$PY" tools/merge/ai_review.py "$BR" 2>&1); RC=$?
        if [ "$RC" = 0 ]; then
          python3 "$REPO/tools/build_loop/ops_log.py" revision approved "$SPECID attempt=$REVISION_ATTEMPT" "\$0" "$BR" "" 2>/dev/null || true
        elif [ "$RC" = 2 ]; then
          python3 "$REPO/tools/build_loop/ops_log.py" revision blocked "$SPECID attempt=$REVISION_ATTEMPT protected-path review" "\$0" "$BR" "James: protected-zone escalation $DID" 2>/dev/null || true
        else
          python3 "$REPO/tools/build_loop/ops_log.py" revision still-flagged "$SPECID attempt=$REVISION_ATTEMPT" "\$0" "$BR" "" 2>/dev/null || true
        fi
      done
      if [ "$RC" != 0 ] && [ "$RC" != 2 ] && [ "$REVISION_ATTEMPT" -ge 2 ]; then
        python3 "$REPO/tools/build_loop/ops_log.py" revision fallback-auto-merge "$SPECID still flagged after 2 attempts" "\$0" "$BR" "" 2>/dev/null || true
      fi
    fi
  fi

  if   [ "$RC" = 0 ]; then ST=built;    V="✅ Built + AI-APPROVED"
  elif [ "$RC" = 2 ]; then ST=rejected; V="🔴 BLOCKED — touches the protected audit layer"
  else                     ST=changes;  V="⚠️ Built, but AI flagged changes"; fi

  dec set-build-result "$DID" "$BR" "$ST" >/dev/null 2>&1 || true
  dec mark-built "$DID" >/dev/null 2>&1 || true
  CNUM=$((CNUM+1)); echo "$TODAY $CNUM" > "$STAMP"

  # AUTO-MERGE on APPROVE or FLAGGED (James directive 2026-06-18: reversible = merge it, don't ask).
  # BLOCKED (RC=2, protected paths) still surfaces — that's a hard stop, not a judgment call.
  # Real merge conflicts still surface — need human judgment on the conflict itself.
  # Flagged-but-merged: logged to ops_ledger only (morning digest), no TG decision ask.
  # Backup = the build/<id> branch + git history. Reversible: `reverse $DID` / git revert. NEVER main.
  MERGED=0
  if [ "$RC" != 2 ]; then
    git -C "$REPO" config user.email ember@fpai >/dev/null 2>&1; git -C "$REPO" config user.name Ember >/dev/null 2>&1
    git -C "$REPO" checkout "$BASE" >/dev/null 2>&1
    PRE_SHA=$(git -C "$REPO" rev-parse HEAD)  # revert point — reset here if health check fails
    if git -C "$REPO" merge --no-edit "$BR" >/dev/null 2>&1; then MERGED=1
    else
      U=$(git -C "$REPO" diff --name-only --diff-filter=U)
      if [ -n "$U" ] && ! echo "$U" | grep -qvE '^(core/BUILD/REGISTRY\.json|docs/codex/HANDOFF\.md|.*/__init__\.py)$'; then
        for f in $U; do git -C "$REPO" checkout --ours "$f" >/dev/null 2>&1; done
        git -C "$REPO" add -A && git -C "$REPO" commit --no-edit >/dev/null 2>&1 && MERGED=1
      else
        git -C "$REPO" merge --abort >/dev/null 2>&1   # real code conflict → leave for human review
      fi
    fi
    if [ "$MERGED" = 1 ]; then
      # post-merge health gate: curator import check (catches syntax errors, broken imports)
      if ! "$PY" -c "import sys; sys.path.insert(0,'$BRAIN'); import curator, curator.decisions" >/dev/null 2>&1; then
        git -C "$REPO" reset --hard "$PRE_SHA" >/dev/null 2>&1
        MERGED=0
        CONSECUTIVE_REVERTS=$((CONSECUTIVE_REVERTS+1))
        tg "🔴 AUTO-REVERTED [$DID] — post-merge import check failed. Rolled back to pre-merge state. Branch $BR held for inspection. Reply <code>reverse $DID</code> to drop."
        python3 "$REPO/tools/build_loop/ops_log.py" merge auto-reverted "$SPECID" "\$0" "$BR" "Ember: inspect $DID — import check failed post-merge" 2>/dev/null || true
        if [ "$CONSECUTIVE_REVERTS" -ge "$CONSECUTIVE_REVERTS_MAX" ]; then
          tg "🔴 BUILD LOOP PAUSED — $CONSECUTIVE_REVERTS consecutive auto-reverts. Specs may be broken or system in bad state. Reply <code>start build</code> or kill switch to resume after inspection."
          python3 "$REPO/tools/build_loop/ops_log.py" build paused "consecutive-reverts=$CONSECUTIVE_REVERTS" "\$0" "" "James: inspect recent builds — pattern of broken imports" 2>/dev/null || true
          echo "halting: $CONSECUTIVE_REVERTS consecutive auto-reverts >= $CONSECUTIVE_REVERTS_MAX"; break
        fi
      else
        dec mark-merged "$DID" >/dev/null 2>&1 || true
        CONSECUTIVE_REVERTS=0  # clean merge resets the revert streak
      fi
    fi
  fi

  if [ "$MERGED" = 1 ]; then
    # Post-merge activation: run activate.sh if the build shipped one
    # Convention: any spec that installs systemd units or needs wiring ships core/BUILD/activate/${SPECID}.sh
    ACTIVATE_SCRIPT="$REPO/core/BUILD/activate/${SPECID}.sh"
    if [ -f "$ACTIVATE_SCRIPT" ]; then
      echo "running activate script for $SPECID"
      bash "$ACTIVATE_SCRIPT" 2>&1 | head -20 || echo "activate script exited non-zero — check $ACTIVATE_SCRIPT"
      python3 "$REPO/tools/build_loop/ops_log.py" merge activated "$SPECID (activate.sh ran)" "\$0" "$BR" "" 2>/dev/null || true
    fi
    run_liveness_probe "$LIVENESS_DECLARATION" "$LIVENESS_CHECK"

    if [ "$RC" = 0 ]; then
      # APPROVE + merged — brief TG confirmation (informational, not a decision ask)
      tg "$V · AUTO-MERGED ✅ [$DID] $SPECID
Landed in feat/headless-build (reversible: <code>reverse $DID</code>)."
      python3 "$REPO/tools/build_loop/ops_log.py" merge auto-merged "$SPECID (AI-approved)" "\$0" "$BR" "" 2>/dev/null || true
    else
      # FLAGGED + merged — ops_ledger only, no TG. Shows in morning digest.
      python3 "$REPO/tools/build_loop/ops_log.py" merge auto-merged-flagged "$SPECID (flagged+reversible)" "\$0" "$BR" "" 2>/dev/null || true
    fi
    echo "auto-merged $SPECID"
  else
    if [ "$RC" = 2 ]; then
      _tail="🔴 BLOCKED — touches the protected layer. Reply <code>reverse $DID</code> to drop."; _ev=blocked; _nx="James: protected-zone escalation $DID"
    else
      _tail="⚠️ Real merge conflict — reply <code>merge $DID</code> after a look."; _ev=conflict; _nx="James: merge conflict $DID"
    fi
    tg "$_tail · [$DID] $SPECID (never main)"
    python3 "$REPO/tools/build_loop/ops_log.py" build "$_ev" "$SPECID ($ST)" "\$0" "$BR" "$_nx" 2>/dev/null || true
    echo "surfaced $SPECID ($ST · awaiting)"
  fi
done <<< "$PENDING"
echo "server build loop done · built $CNUM today"
