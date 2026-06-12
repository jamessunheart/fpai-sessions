#!/usr/bin/env bash
# sovereign_benchmark.sh — Day 5 quality benchmark
# Runs the same 5 routine task prompts through both Opus (via Claude Code) and
# the sovereign track (local 32B or remote 70B). Captures responses + duration.
# Comparison + <85% threshold scoring done in a follow-up review pass.
#
# Usage:
#   sovereign_benchmark.sh                    # runs all 5 against sovereign default
#   sovereign_benchmark.sh --tier 70b         # benchmark remote H100
#   sovereign_benchmark.sh --task kai_sweep   # single task only
#
# Output:
#   ~/.config/fpai/sovereign_phase1/benchmark_<UTC-timestamp>/
#     task_1_kai_sweep__sovereign.txt
#     task_1_kai_sweep__sovereign.meta.json   (duration, model, tier)
#     ...
#     SUMMARY.md  (aggregated meta · ready for side-by-side review)

set -euo pipefail

TIER_ARG=""
ONLY_TASK=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tier) TIER_ARG="--tier $2"; shift 2 ;;
    --task) ONLY_TASK="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 4 ;;
  esac
done

STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
OUTDIR="$HOME/.config/fpai/sovereign_phase1/benchmark_$STAMP"
mkdir -p "$OUTDIR"
ROUTER="$(dirname "$0")/sovereign_chat.sh"

# 5 task types, mirroring real Kai/Forge/Narrator/digest/classifier work
declare -a TASKS=(
  "kai_sweep|Scan this list of 12 git commits and classify each as (a) feature, (b) bugfix, (c) chore, (d) docs. Return one classification per line in format 'commit_hash: type'. Commits: 945594bf chore(identity): SETTLE 2026-05-19; 52f22de2 feat(content-pipeline): wire Content Pipeline V1; 7568cecd chore(security): scrub leaked keys; 4f98d085 feat(reset): landing redirect; 428c495a feat(reset): payment page; 51851277 fix(hook): collision prevention; 8b8a64de fix(commit): unbundled siblings; e91234ab docs(narrator): observation log template; f01b2cd3 chore(memory): prune stale; 0192abc4 feat(treasury): SSOT discipline; 9aabcdef fix(brain): pgvector index; 12345678 refactor(forge): weekly autopilot."
  "inventory_diff|Given two capability inventories (before/after), identify which agents were added, removed, or upgraded. BEFORE: [ember, kai, forge, narrator, treasurer]. AFTER: [ember, kai, forge, narrator, treasurer, churn, growth-architect, sunheart-distiller, james-hour-optimizer]. Return concise diff."
  "digest_summary|Summarize this week's progress in 3 bullets max (caveman clarity, ≤80 words total): Built sovereign-stack Phase 0 recon; got James greenlight on 4 strategic-frame questions; shipped sovereign_chat.sh router; wrote Forge weekly autopilot dispatch; published 5 episodic-memory updates; identity files refactored with APPRENTICESHIP clause; treasury bootstrap at $500 HL baseline 0; Camp Zen architecture flipped retreat→continuous-village; Narrator agent named and Phase 0 launched; PULSE ledger now cross-session."
  "question_classify|Classify each of these into one of {strategic_frame, tactical_task, status_question, soul_check}: (1) Should we own a Mac Studio in Q3? (2) Did the brain ingest finish? (3) What feels most alive in the work today? (4) Move SOL short to JitoSOL? (5) Is the Game enrollment funnel coherent? (6) Did James settle yesterday's session?"
  "rename_suggest|Suggest better filenames for these 5 scratch files. Constraint: kebab-case, ≤50 chars, prefix with type (feedback_/project_/reference_). Files: 'thing_about_money.md', 'idea james.md', 'temp_notes_for_camp.md', 'why_ai_matters.md', 'random_thought_on_continuity.md'."
)

run_task() {
  local key="$1" prompt="$2"
  local outbase="$OUTDIR/task_${key}__sovereign"
  printf '%s' "$prompt" > "${outbase}.prompt.txt"
  local start_epoch end_epoch dur
  start_epoch="$(date +%s)"
  if "$ROUTER" $TIER_ARG "$prompt" > "${outbase}.response.txt" 2>"${outbase}.err.txt"; then
    end_epoch="$(date +%s)"
    dur=$(( end_epoch - start_epoch ))
    printf '{"task":"%s","status":"ok","duration_s":%d,"tier_arg":"%s"}\n' \
      "$key" "$dur" "$TIER_ARG" > "${outbase}.meta.json"
    echo "[ok] $key in ${dur}s"
  else
    printf '{"task":"%s","status":"error"}\n' "$key" > "${outbase}.meta.json"
    echo "[ERROR] $key (see ${outbase}.err.txt)"
  fi
}

for entry in "${TASKS[@]}"; do
  key="${entry%%|*}"
  prompt="${entry#*|}"
  if [[ -n "$ONLY_TASK" && "$key" != "$ONLY_TASK" ]]; then
    continue
  fi
  run_task "$key" "$prompt"
done

# Aggregate SUMMARY.md
{
  echo "# Sovereign Benchmark · $STAMP"
  echo ""
  echo "Router: $ROUTER · tier args: \`$TIER_ARG\`"
  echo ""
  echo "| Task | Status | Duration (s) |"
  echo "|---|---|---|"
  for entry in "${TASKS[@]}"; do
    key="${entry%%|*}"
    meta="$OUTDIR/task_${key}__sovereign.meta.json"
    if [[ -f "$meta" ]]; then
      status=$(jq -r '.status' "$meta")
      dur=$(jq -r '.duration_s // "-"' "$meta")
      echo "| $key | $status | $dur |"
    fi
  done
  echo ""
  echo "Next step: pair each \`task_*__sovereign.response.txt\` with the same prompt run through Opus (Claude Code), score quality 0-100%, log to PHASE1_BENCHMARK_RESULTS.md. Tasks scoring <85% three times re-escalate to Opus permanently per cutover policy."
} > "$OUTDIR/SUMMARY.md"

echo ""
echo "Benchmark complete · $OUTDIR/SUMMARY.md"
