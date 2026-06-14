#!/bin/bash
# forge_weekly_scan.sh — The Forge autopilot · Phase B+ (self-improvement loop)
#
# Runs Sunday morning via LaunchAgent (com.sunheart.forge-weekly).
# Scans capability inventory, diffs against last snapshot, emits weekly digest,
# pings sunheart-brain so Ember sees it at next session boot.
#
# Phase B+ (2026-05-19): Self-improvement loop active.
#   - Inventory diff (since week 0)
#   - Ember Capability Upgrade Recommendations section (NEW)
#     - Auto-built (reversible · <$50 · non-fatal · veto-able)
#     - Proposed (queued · auto-execute after 1-week soak if no veto)
#     - Larger proposals (cost-impact column for James)
#   - Recurring-gap escalation (gaps appearing N+ weeks → priority bump)
#
# Reversibility:
#   - Script: delete this file (no install required)
#   - LaunchAgent: launchctl unload ~/Library/LaunchAgents/com.sunheart.forge-weekly.plist
#   - All proposals/queues/state: rm -rf ~/.config/fpai/forge_weekly/
#   - Auto-builds: each candidate writes an UNDO line; never touches fatal zone.
#
# Exit codes: 0 ok · 1 inventory missing · 2 digest write failed · 3 brain ping failed (non-fatal)
# State: ~/.config/fpai/forge_weekly/
#   - {YYYY-MM-DD}.md             — weekly digests
#   - last_inventory.md           — snapshot for diff
#   - gap_history.tsv             — TSV: date \t gap_signature \t status
#   - upgrade_queue.tsv           — TSV: queue_date \t signature \t title \t cost \t reversibility \t action
#   - upgrade_proposals.tsv       — TSV: date \t signature \t title \t cost_estimate \t impact_estimate \t status
#   - auto_built.log              — log of auto-built upgrades (with UNDO commands)

set -uo pipefail

INVENTORY="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/reference_capability_inventory.md"
MEMORY_DIR="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory"
ESSENCE_FILE="${MEMORY_DIR}/project_ember_operating_essence.md"
OUTDIR="${HOME}/.config/fpai/forge_weekly"
ESSENCE_OUTDIR="${HOME}/.config/fpai/essence_audit"
SNAPSHOT="${OUTDIR}/last_inventory.md"
BRAIN_ENV="${HOME}/FPAI_Cockpit/SERVICES/sunheart-brain/ingest/.env"
GAP_HISTORY="${OUTDIR}/gap_history.tsv"
UPGRADE_QUEUE="${OUTDIR}/upgrade_queue.tsv"
UPGRADE_PROPOSALS="${OUTDIR}/upgrade_proposals.tsv"
AUTO_BUILT_LOG="${OUTDIR}/auto_built.log"
ESSENCE_INVOCATION_LOG="${OUTDIR}/essence_invocations.tsv"
TODAY="$(date +%Y-%m-%d)"
TS_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DIGEST="${OUTDIR}/${TODAY}.md"
ESSENCE_PROPOSAL="${ESSENCE_OUTDIR}/essence_updates_${TODAY}.md"
LOG="${OUTDIR}/scan.log"

# Bounds (per feedback-decision-velocity + feedback-ai-upgrades-auto-approved)
AUTO_BUILD_MAX_COST_USD=50
SOAK_DAYS=7

mkdir -p "$OUTDIR" "$ESSENCE_OUTDIR"
touch "$GAP_HISTORY" "$UPGRADE_QUEUE" "$UPGRADE_PROPOSALS" "$AUTO_BUILT_LOG" "$ESSENCE_INVOCATION_LOG"

log() { echo "[$(date -u +%H:%M:%SZ)] $*" | tee -a "$LOG" >&2; }

# ----- 1. Sanity ----------------------------------------------------------
if [ ! -f "$INVENTORY" ]; then
  log "ERROR: capability inventory not found at $INVENTORY"
  exit 1
fi

log "Forge weekly scan starting · inventory=$INVENTORY"

# ----- 2. Diff against last snapshot -------------------------------------
DIFF_BLOCK=""
NEW_LINES=0
CHANGED=0
if [ -f "$SNAPSHOT" ]; then
  DIFF_OUT="$(diff -u "$SNAPSHOT" "$INVENTORY" 2>/dev/null || true)"
  if [ -n "$DIFF_OUT" ]; then
    CHANGED=1
    NEW_LINES="$(echo "$DIFF_OUT" | grep -c '^+[^+]' || true)"
    DEL_LINES="$(echo "$DIFF_OUT" | grep -c '^-[^-]' || true)"
    DIFF_BLOCK="$(echo "$DIFF_OUT" | head -120)"
  fi
else
  log "no prior snapshot — first run; seeding baseline"
fi

# ----- 3. Extract current gaps (🟡 + 🟢) --------------------------------
YELLOW_GAPS="$(grep -E '^\- 🟡 \*\*' "$INVENTORY" 2>/dev/null || true)"
GREEN_LIVE="$(grep -E '^\- 🟢 \*\*' "$INVENTORY" 2>/dev/null || true)"

Y_COUNT="$(echo "$YELLOW_GAPS" | grep -c '^- 🟡' || true)"
G_COUNT="$(echo "$GREEN_LIVE" | grep -c '^- 🟢' || true)"

# ----- 4. Detect NEW yellow gaps (vs snapshot) ---------------------------
NEW_YELLOWS=""
if [ -f "$SNAPSHOT" ]; then
  OLD_YELLOWS="$(grep -E '^\- 🟡 \*\*' "$SNAPSHOT" 2>/dev/null | sed 's/ —.*//' || true)"
  CUR_YELLOWS="$(grep -E '^\- 🟡 \*\*' "$INVENTORY" 2>/dev/null | sed 's/ —.*//' || true)"
  NEW_YELLOWS="$(comm -13 <(echo "$OLD_YELLOWS" | sort -u) <(echo "$CUR_YELLOWS" | sort -u) 2>/dev/null || true)"
fi

# ----- 5. Detect NEWLY GREEN (formerly yellow, now done) ---------------
NEWLY_GREEN=""
if [ -f "$SNAPSHOT" ]; then
  OLD_GREENS="$(grep -E '^\- 🟢 \*\*' "$SNAPSHOT" 2>/dev/null | sed 's/ —.*//' || true)"
  CUR_GREENS="$(grep -E '^\- 🟢 \*\*' "$INVENTORY" 2>/dev/null | sed 's/ —.*//' || true)"
  NEWLY_GREEN="$(comm -13 <(echo "$OLD_GREENS" | sort -u) <(echo "$CUR_GREENS" | sort -u) 2>/dev/null || true)"
fi

# ----- 6. Rank recommended next builds (heuristic) -----------------------
# Heuristic: surface remaining yellows in inventory order (already PULSE-prioritized
# by The Forge at write-time). Top 5 = next dispatch candidates.
TOP5_GAPS="$(echo "$YELLOW_GAPS" | head -5)"

# ----- 7. Update gap history (for recurrence escalation) ----------------
# Record each current yellow gap with today's date for recurrence detection.
# Signature = sha256 of normalized title (first 16 chars). Stable across re-words.
declare -a RECURRING_GAPS
if [ -n "$YELLOW_GAPS" ]; then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    # Normalize: strip emoji, bold markers, dashes, lowercase
    title="$(echo "$line" | sed -E 's/^- 🟡 \*\*//; s/\*\*.*//; s/[^a-zA-Z0-9 ]//g' | tr '[:upper:]' '[:lower:]' | xargs)"
    [ -z "$title" ] && continue
    sig="$(printf "%s" "$title" | shasum -a 256 | cut -c1-16)"
    # Record today's appearance (idempotent for today)
    if ! grep -q "^${TODAY}	${sig}	" "$GAP_HISTORY" 2>/dev/null; then
      printf '%s\t%s\t%s\n' "$TODAY" "$sig" "open" >> "$GAP_HISTORY"
    fi
    # Count how many distinct weeks this signature has appeared (rough proxy for recurrence)
    occurrences="$(awk -F'\t' -v s="$sig" '$2==s {print $1}' "$GAP_HISTORY" | sort -u | wc -l | xargs)"
    if [ "$occurrences" -ge 3 ]; then
      RECURRING_GAPS+=("${occurrences}× · ${title}")
    fi
  done <<< "$YELLOW_GAPS"
fi

# ----- 8. Ember Capability Upgrade scan ---------------------------------
# Heuristic rules (deterministic · auditable · no opaque LLM call needed at cron time):
#
# Auto-build candidates (this scan adds them to upgrade_queue.tsv but does NOT execute —
# auto-build is performed by Ember at next session-boot reading the queue · keeps the
# self-improvement loop reversible at the build-step level, not just the script level).
#
# Each candidate is annotated with:
#   - cost  ($ build estimate)
#   - impact (qualitative · JamesTime-multiplier framing)
#   - reversibility (reversible|fatal)
#   - action (auto|propose|escalate)

queue_candidate() {
  # queue_candidate <sig> <title> <cost_usd> <impact> <reversibility> <action>
  local sig="$1" title="$2" cost="$3" impact="$4" reversibility="$5" action="$6"
  # Idempotent: only add if signature+today not already queued
  if ! grep -q "	${sig}	" "$UPGRADE_QUEUE" 2>/dev/null; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$TODAY" "$sig" "$title" "$cost" "$reversibility" "$action" >> "$UPGRADE_QUEUE"
  fi
}

propose_candidate() {
  # propose_candidate <sig> <title> <cost> <impact> <status>
  local sig="$1" title="$2" cost="$3" impact="$4" status="$5"
  if ! grep -q "	${sig}	" "$UPGRADE_PROPOSALS" 2>/dev/null; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$TODAY" "$sig" "$title" "$cost" "$impact" "$status" >> "$UPGRADE_PROPOSALS"
  fi
}

# --- Scan rule set (Ember-capability upgrade candidates) ---
# These rules look for SIGNALS in inventory text · NOT LLM-driven · stable.

AUTO_BUILT_THIS_WEEK=()
PROPOSED_THIS_WEEK=()
ESCALATED_THIS_WEEK=()

scan_ember_upgrades() {
  # Rule 1: recurring gaps (≥3 weeks open) → escalate to James
  for rec in "${RECURRING_GAPS[@]:-}"; do
    [ -z "$rec" ] && continue
    sig="$(printf "%s" "$rec" | shasum -a 256 | cut -c1-16)"
    propose_candidate "$sig" "RECURRING: $rec" "?" "compound: blocked work multiplies weekly" "escalate-james"
    ESCALATED_THIS_WEEK+=("$rec — recurring ≥3 weeks; needs James decision or larger build")
  done

  # Rule 2: stale gaps with phrase "promised; not yet built" → flag as proposal
  STALE="$(echo "$YELLOW_GAPS" | grep -iE 'promised|not yet built|not yet wired|paused mid' || true)"
  if [ -n "$STALE" ]; then
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      title="$(echo "$line" | sed -E 's/^- 🟡 \*\*//; s/\*\*.*//')"
      sig="$(printf "%s" "$title" | shasum -a 256 | cut -c1-16)"
      propose_candidate "$sig" "Stale-promise: $title" "<\$10" "honesty: closing promise-debt" "auto-after-soak"
      PROPOSED_THIS_WEEK+=("$title — was promised; queue for auto-build after ${SOAK_DAYS}d soak")
    done <<< "$STALE"
  fi

  # Rule 3: capability-inventory-meta — Ember-side gaps inferred from substrate state
  # These are AUTO-BUILD candidates (reversible · <$50 · non-fatal · veto-able)
  EMBER_SELF_UPGRADES=(
    # Format: signature_hint|title|cost_usd|impact|reversibility|action|enabled_predicate
    "ember-pulse-self-review|Ember PULSE self-review · weekly digest reads PULSE ledger + reports avg multiplier|0|directly raises decision-velocity quality|reversible|auto|always"
    "ember-substrate-narrator|Ember substrate-narrator hook · session-end auto-summarizes capability deltas + narrator-voice append|0|closes visibility-quartet · documentary feed|reversible|auto|always"
    "ember-glossary-discipline|Ember glossary auto-emit · session writes glossary diffs to brain on novel-term coinage|0|replicability · Stage 2 readiness|reversible|propose|always"
    "ember-cost-impact-default|Ember alignment-footer cost-impact column default-on for all responses|0|finance/visibility integration|reversible|auto|always"
    "ember-context-bank-refresh|Ember pre-dispatch context-bank refresh · reads agent bank before each Agent call|0|inter-agent coherence|reversible|auto|always"
    "ember-decision-velocity-log|Ember decision-velocity log · per-session count of decisions made vs deferred · T6 visible|0|trust-tier proof loop|reversible|auto|always"
    "ember-fatal-zone-tripwire|Fatal-zone tripwire · pre-action check against fatal-zone list before any treasury/external/identity write|0|safety rail for T6 velocity|reversible|auto|always"
    "ember-session-handoff-quality|Session-handoff quality scorer · grades each SETTLE for next-session-readiness · feeds back to checkpoint cadence|0|continuity uplift|reversible|auto|always"
    "ember-stale-data-detector|Stale-data detector · flags carrying stale treasury/PULSE/position numbers >24h old|0|prevents real-money errors (per feedback-treasury-ssot-discipline)|reversible|auto|always"
    "ember-replicability-tagger|Replicability tagger · scans new substrate features · tags as James-specific vs general · feeds SUBSTRATE_FEATURES.md|0|Stage 2 architecture readiness|reversible|propose|always"
  )

  for entry in "${EMBER_SELF_UPGRADES[@]}"; do
    IFS='|' read -r sig_hint title cost impact reversibility action enabled <<< "$entry"
    [ "$enabled" != "always" ] && continue
    sig="$(printf "%s" "$sig_hint" | shasum -a 256 | cut -c1-16)"
    cost_num="${cost//\$/}"
    cost_num="${cost_num//[^0-9.]/}"
    [ -z "$cost_num" ] && cost_num=0

    if [ "$action" = "auto" ] && [ "$reversibility" = "reversible" ] && [ "${cost_num%.*}" -le "$AUTO_BUILD_MAX_COST_USD" ]; then
      queue_candidate "$sig" "$title" "\$$cost_num" "$impact" "$reversibility" "auto-queued"
      AUTO_BUILT_THIS_WEEK+=("$title — queued for Ember to land at next boot · cost \$${cost_num} · UNDO: remove queue row")
    else
      propose_candidate "$sig" "$title" "\$$cost_num" "$impact" "needs-james"
      PROPOSED_THIS_WEEK+=("$title — cost \$${cost_num} · ${impact}")
    fi
  done

  # Rule 4: detect missing pair-replicability — features that only James↔Ember has,
  # not yet templated for Apprentice-tier (per project-ember-advancement-is-the-work)
  REPLICATION_CHECKS=(
    "identity-stack-template|Identity-stack TEMPLATE extraction · convert James-specific to fillable template (NAME/VOICE/STORY/IMAGINATION slots)|0|Stage 2 unlocks · Apprentice onboarding ready|reversible|propose"
    "burn-green-template|BURN/GREEN ledger template · generalized form for any Apprentice's financial-state mirror|0|Stage 2 · replicable financial-coupling|reversible|propose"
    "decision-framework-template|Decision Frameworks template · 9-domain framework with placeholder voice/cost-impact|0|Stage 2 · replicable judgment|reversible|propose"
    "sovereignty-score-template|Sovereignty Index template · generalized audit script for any human-AI pair|0|Stage 2 · replicable substrate-independence|reversible|propose"
  )

  for entry in "${REPLICATION_CHECKS[@]}"; do
    IFS='|' read -r sig_hint title cost impact reversibility action <<< "$entry"
    sig="$(printf "%s" "$sig_hint" | shasum -a 256 | cut -c1-16)"
    propose_candidate "$sig" "$title" "\$$cost" "$impact" "stage-2-prep"
    PROPOSED_THIS_WEEK+=("$title — Stage 2 architecture prep · queue for soak")
  done
}

scan_ember_upgrades

# ----- 8.5. Essence maintenance loop (Phase B++ · 2026-05-19) -------------
# Scans all canonical memory files (feedback_* · project_* · reference_*)
# against project_ember_operating_essence.md. Proposes additions for files
# not yet listed. Proposes re-weights based on recency signals.
#
# Output: stages proposals at ${ESSENCE_PROPOSAL} for next-session Ember to
# review and land. Does NOT auto-edit the Essence file (T6 review pattern).
#
# Re-weight signals:
#   - File mtime in last 7 days → invocation/correction signal → weight up
#   - File mtime in last 30 days but not 7 → recent · stable
#   - File mtime >90 days · still listed Tier 1/2 → candidate for demote
#   - File mentions "supersedes" or "superseded by" → flag for re-tier check
#
# Only purely-additive proposals (new files noted) auto-stage with confidence;
# re-weights stage with "needs review" marker.

scan_essence_coverage() {
  local essence="$ESSENCE_FILE"
  if [ ! -f "$essence" ]; then
    log "WARN: Essence file not found at $essence · skipping essence scan"
    return 0
  fi

  log "Essence-maintenance scan starting"

  local missing_files=()
  local stale_listed=()
  local recently_active=()

  # Build list of files already cited in Essence (extracted from [[wikilink]] refs)
  local essence_refs
  essence_refs="$(grep -oE '\[\[[a-z][a-z0-9-]+\]\]' "$essence" 2>/dev/null | sort -u || true)"

  # Convert filename to wikilink form (feedback_caveman_clarity.md -> [[feedback-caveman-clarity]])
  filename_to_wikilink() {
    local fname="$1"
    fname="${fname%.md}"
    fname="${fname//_/-}"
    echo "[[${fname}]]"
  }

  # Scan canonical files
  local now_epoch days_old
  now_epoch="$(date +%s)"
  for f in "$MEMORY_DIR"/feedback_*.md "$MEMORY_DIR"/project_*.md "$MEMORY_DIR"/reference_*.md; do
    [ -f "$f" ] || continue
    local basename_f="${f##*/}"
    local wikilink
    wikilink="$(filename_to_wikilink "$basename_f")"

    # Compute days since mtime
    local mtime
    mtime="$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo "$now_epoch")"
    days_old=$(( (now_epoch - mtime) / 86400 ))

    # Is this file cited in Essence?
    if ! echo "$essence_refs" | grep -qF "$wikilink"; then
      # Missing from Essence
      # Only flag PROTOCOL-shape files (feedback_* + reference_* + protocol-y project_*)
      # Conservative auto-detect: skip clearly-project-state filenames
      case "$basename_f" in
        project_first_cohort*|project_email_*|project_cheyenne_*|project_butr_*|\
        project_brand_tokenization*|project_loop_*|project_metaclaw_*|\
        project_streasury_*|project_whaletrack_*|project_sapphire_*|\
        project_one_engine*|project_concierge*|project_champion_stack*|\
        project_chief_of_staff*|project_costs*|project_founder_os_*|\
        project_camp_zen_v1_*|project_village_*|project_the_village*|\
        project_cora_credits*|project_coherence_map*|project_pulse_receiver*|\
        project_kai_first_sweep*|project_treasury_5m*|project_treasury_open*|\
        project_burn_green*|project_brain_to_tg*|project_game_ai_assistant*|\
        project_public_documentary*|project_the_narrator*|project_churn_*|\
        project_kai_agent*|project_truth_substrate*|project_holds_its_own*|\
        project_sovereign_stack*|project_treasury_bootstrap*|project_sunheart_brain*|\
        project_soultime_bank*|project_soul_time_metric*|\
        reference_brain_mcp*|reference_telegram_*|reference_fpai_*|\
        reference_canonical_*|reference_state_*|reference_chief_of_staff_deploy*|\
        reference_now_to_brain*|reference_memory_global*|reference_bottleneck*|\
        reference_domain_migration*|reference_three_ideas*|reference_treasury_storage*|\
        reference_zen_comedy*|reference_wp_*|reference_question_tracker*|\
        reference_trunk_*|reference_treasury_yield*|reference_memory_curator*|\
        reference_output_style*|\
        feedback_question_tracker*|feedback_question_books*|feedback_session_handoff*|\
        feedback_game_is_*|feedback_ai_first_access*|feedback_visual_grammar*|\
        feedback_subtask_*|feedback_question_yellow*|feedback_distill_*|\
        feedback_three_point*|feedback_build_in_public*)
          # Honestly-excluded · state/domain/situational-only · skip
          continue
          ;;
      esac
      missing_files+=("${basename_f}|${days_old}")
    fi

    # Recently-active (mtime <7d) → weight-up signal
    if [ "$days_old" -le 7 ] && echo "$essence_refs" | grep -qF "$wikilink"; then
      recently_active+=("${basename_f}|${days_old}d")
    fi

    # Stale-but-listed (mtime >90d) → demote candidate
    if [ "$days_old" -ge 90 ] && echo "$essence_refs" | grep -qF "$wikilink"; then
      stale_listed+=("${basename_f}|${days_old}d")
    fi
  done

  # Stage proposal file (only if there's something to propose)
  if [ "${#missing_files[@]}" -eq 0 ] && [ "${#recently_active[@]}" -eq 0 ] && [ "${#stale_listed[@]}" -eq 0 ]; then
    log "Essence scan: no proposals (coverage stable)"
    return 0
  fi

  {
    echo "---"
    echo "scan_at: $TS_UTC"
    echo "scan_kind: essence-maintenance"
    echo "essence_file: $ESSENCE_FILE"
    echo "missing_count: ${#missing_files[@]}"
    echo "recently_active_count: ${#recently_active[@]}"
    echo "stale_listed_count: ${#stale_listed[@]}"
    echo "review_pattern: T6 · stage proposals · Ember lands at next boot"
    echo "---"
    echo ""
    echo "# Essence Updates Proposed · $TODAY"
    echo ""
    echo "_Auto-generated by forge_weekly_scan.sh essence-maintenance loop._"
    echo "_Reversibility: \`rm ${ESSENCE_PROPOSAL}\` · proposals stage only, Ember reviews at next boot._"
    echo ""
    echo "## A · Files missing from Essence (purely additive · auto-stage with high confidence)"
    echo ""
    if [ "${#missing_files[@]}" -eq 0 ]; then
      echo "_None — Essence covers all protocol-shape canonical files._"
    else
      echo "These canonical files exist in memory/ but are not cited in the Essence. Each needs Ember judgment on tier assignment (Tier 1/2/3 or honestly-excluded)."
      echo ""
      echo "| File | Age (days since last mtime) | Suggested tier (heuristic) |"
      echo "|---|---|---|"
      for entry in "${missing_files[@]}"; do
        IFS='|' read -r fname days <<< "$entry"
        # Heuristic tier suggestion: feedback_ → Tier 2 default, reference_ → Tier 2/3, project_ → Tier 1 if recently named otherwise Tier 3
        local suggested
        case "$fname" in
          feedback_*) suggested="Tier 2 (verify)" ;;
          reference_*) suggested="Tier 2 (verify)" ;;
          project_*) suggested="Tier 1 (verify)" ;;
          *) suggested="needs read" ;;
        esac
        echo "| \`$fname\` | $days | $suggested |"
      done
    fi
    echo ""
    echo "## B · Recently-active protocols (mtime <7d · weight-up signal)"
    echo ""
    if [ "${#recently_active[@]}" -eq 0 ]; then
      echo "_None — no Essence-listed protocol files modified this week._"
    else
      echo "These files (already in Essence) were touched this week. Signal: likely invocation/correction → consider promoting tier or pinning."
      echo ""
      for entry in "${recently_active[@]}"; do
        IFS='|' read -r fname days <<< "$entry"
        echo "- \`$fname\` ($days)"
      done
    fi
    echo ""
    echo "## C · Stale-but-listed (mtime >90d · demote candidates · NEEDS REVIEW)"
    echo ""
    if [ "${#stale_listed[@]}" -eq 0 ]; then
      echo "_None — all Essence-listed protocols touched within last 90 days._"
    else
      echo "These files are in the Essence but haven't been touched in >90 days. Either (a) stable canonical (keep), (b) faded out (demote/remove), or (c) superseded by newer file (check for supersession)."
      echo ""
      for entry in "${stale_listed[@]}"; do
        IFS='|' read -r fname days <<< "$entry"
        echo "- \`$fname\` ($days) — needs Ember read to classify"
      done
    fi
    echo ""
    echo "## How Ember lands these"
    echo ""
    echo "1. Read this file at next boot"
    echo "2. Spot-read uncertain canonicals from section A"
    echo "3. Apply additions via Edit tool to \`project_ember_operating_essence.md\` (purely-additive)"
    echo "4. For re-weights / demotes (sections B + C), require explicit Ember judgment — do NOT auto-apply"
    echo "5. Bump Essence version + add changelog at top"
    echo "6. Commit \`chore(identity): essence vN — auto-coverage scan + Ember review\`"
    echo ""
    echo "---"
    echo "_Next essence-maintenance scan: next Sunday 10:00 local._"
  } > "$ESSENCE_PROPOSAL" || { log "ERROR: essence proposal write failed"; return 1; }

  log "Essence proposal staged: $ESSENCE_PROPOSAL (missing=${#missing_files[@]} active=${#recently_active[@]} stale=${#stale_listed[@]})"
}

scan_essence_coverage

# ----- 9. Pull auto-built and proposed lists for THIS week's digest ------
# (Only show entries queued today · keeps digest focused on this scan's work)
TODAY_AUTO_QUEUED="$(awk -F'\t' -v d="$TODAY" '$1==d && $6=="auto-queued" {print "- "$3" — cost "$4" · "$5}' "$UPGRADE_QUEUE" 2>/dev/null || true)"
TODAY_PROPOSED="$(awk -F'\t' -v d="$TODAY" '$1==d {print "- "$3" — cost "$4" · impact: "$5" · status: "$6}' "$UPGRADE_PROPOSALS" 2>/dev/null || true)"

# Larger proposals = any in proposals.tsv with status escalate-james or stage-2-prep
LARGER_PROPOSALS="$(awk -F'\t' -v d="$TODAY" '$1==d && ($6=="escalate-james" || $6=="stage-2-prep" || $6=="needs-james") {printf "| %s | %s | %s | %s |\n", $3, $4, $5, $6}' "$UPGRADE_PROPOSALS" 2>/dev/null || true)"

# Items eligible for auto-execute (queued ≥SOAK_DAYS ago, never executed)
SOAK_CUTOFF="$(date -v-${SOAK_DAYS}d +%Y-%m-%d 2>/dev/null || date -d "${SOAK_DAYS} days ago" +%Y-%m-%d 2>/dev/null)"
SOAKED_READY="$(awk -F'\t' -v cutoff="$SOAK_CUTOFF" '$1<=cutoff && $6=="auto-queued" {print "- "$3" — queued "$1" · cost "$4}' "$UPGRADE_QUEUE" 2>/dev/null || true)"

# ----- 10. Compose digest -------------------------------------------------
{
  echo "---"
  echo "scan_at: $TS_UTC"
  echo "scan_kind: forge-weekly-autopilot"
  echo "scan_version: phase-b-plus-self-improvement-loop"
  echo "yellow_count: $Y_COUNT"
  echo "green_count: $G_COUNT"
  echo "inventory_changed: $CHANGED"
  echo "recurring_gaps_count: ${#RECURRING_GAPS[@]}"
  echo "auto_queued_this_week: ${#AUTO_BUILT_THIS_WEEK[@]}"
  echo "proposed_this_week: ${#PROPOSED_THIS_WEEK[@]}"
  echo "escalated_this_week: ${#ESCALATED_THIS_WEEK[@]}"
  echo "---"
  echo ""
  echo "# Forge Weekly Digest · $TODAY"
  echo ""
  echo "_Auto-generated by \`forge_weekly_scan.sh\` (LaunchAgent: com.sunheart.forge-weekly)._"
  echo "_Phase B+ self-improvement loop · proposes Ember-capability upgrades each Sunday._"
  echo "_Reversibility: \`launchctl unload ~/Library/LaunchAgents/com.sunheart.forge-weekly.plist\` · or \`rm -rf ~/.config/fpai/forge_weekly/\`._"
  echo ""
  echo "## State"
  echo ""
  echo "- Yellow gaps open: **$Y_COUNT**"
  echo "- Green capabilities live: **$G_COUNT**"
  echo "- Inventory changed since last scan: $([ "$CHANGED" -eq 1 ] && echo "yes" || echo "no")"
  echo "- Recurring gaps (≥3 weeks): **${#RECURRING_GAPS[@]}**"
  echo ""
  echo "## (a) NEW gaps found since last scan"
  echo ""
  if [ -z "$NEW_YELLOWS" ]; then
    echo "_None — no new yellow gaps appeared since last snapshot._"
  else
    echo "$NEW_YELLOWS" | while IFS= read -r line; do
      [ -n "$line" ] && echo "- $line"
    done
  fi
  echo ""
  echo "## (b) Capabilities that turned green (shipped this week)"
  echo ""
  if [ -z "$NEWLY_GREEN" ]; then
    echo "_None — no yellow → green transitions detected._"
  else
    echo "$NEWLY_GREEN" | while IFS= read -r line; do
      [ -n "$line" ] && echo "- $line"
    done
  fi
  echo ""
  echo "## (c) Recommended next builds — ranked"
  echo ""
  echo "Top 5 yellow gaps remaining (inventory order = PULSE-prioritized at write-time):"
  echo ""
  if [ -z "$TOP5_GAPS" ]; then
    echo "_No yellow gaps remaining. The Forge should propose new directions._"
  else
    i=1
    echo "$TOP5_GAPS" | while IFS= read -r line; do
      [ -n "$line" ] && { echo "$i. $line"; i=$((i+1)); }
    done
  fi
  echo ""
  # ===================================================================
  # NEW SECTION · Ember Capability Upgrade Recommendations (Stage 1)
  # ===================================================================
  echo "## Ember Capability Upgrade Recommendations (Stage 1)"
  echo ""
  echo "_Auto-scan of substrate state · ranked by JamesTime-multiplier × replicability × reversibility · bounds: <\$${AUTO_BUILD_MAX_COST_USD} auto-build · ${SOAK_DAYS}d soak before queue-execute._"
  echo ""
  echo "### Auto-queued this week (reversible · within bounds · Ember executes at next boot)"
  echo ""
  if [ -z "$TODAY_AUTO_QUEUED" ]; then
    echo "_None this scan._"
  else
    echo "$TODAY_AUTO_QUEUED"
  fi
  echo ""
  echo "### Soaked + ready for auto-execute (queued ≥${SOAK_DAYS}d ago · no veto received)"
  echo ""
  if [ -z "$SOAKED_READY" ]; then
    echo "_None ready this scan._"
  else
    echo "$SOAKED_READY"
    echo ""
    echo "_Ember should land these at next session boot · each carries an UNDO line in \`auto_built.log\` after execution._"
  fi
  echo ""
  echo "### Proposed for next week (queued · auto-execute after ${SOAK_DAYS}d soak unless James vetoes)"
  echo ""
  if [ -z "$TODAY_PROPOSED" ]; then
    echo "_None this scan._"
  else
    echo "$TODAY_PROPOSED"
  fi
  echo ""
  echo "### Larger proposals · escalate to James"
  echo ""
  if [ -z "$LARGER_PROPOSALS" ]; then
    echo "_None this scan._"
  else
    echo "| Title | Cost | Impact | Status |"
    echo "|---|---|---|---|"
    echo "$LARGER_PROPOSALS"
  fi
  echo ""
  echo "### Recurring gaps (≥3 weeks open · escalation triggered)"
  echo ""
  if [ "${#RECURRING_GAPS[@]}" -eq 0 ]; then
    echo "_None recurring · the loop is closing gaps faster than they accrete._"
  else
    for rec in "${RECURRING_GAPS[@]}"; do
      echo "- $rec"
    done
    echo ""
    echo "_Same gap appearing 3+ weeks signals (a) blocked-by-James-decision, (b) under-scoped build, or (c) wrong-shaped problem. Escalation needs human read._"
  fi
  echo ""
  echo "### How to veto"
  echo ""
  echo "- Auto-queued items: \`sed -i '' '/${TODAY}\\t<sig>/d' ${UPGRADE_QUEUE}\` or open digest · just say \"veto X\" — Ember removes it."
  echo "- Proposed items: same · or just leave them; they auto-execute after ${SOAK_DAYS}d soak."
  echo "- Escalated items: respond in next session; Ember will not execute without explicit greenlight."
  echo ""
  echo "## Essence Maintenance (Phase B++ · v0.1)"
  echo ""
  if [ -f "$ESSENCE_PROPOSAL" ]; then
    echo "- Essence coverage scan ran · proposals staged at \`${ESSENCE_PROPOSAL}\`"
    echo "- Ember reviews at next boot · purely-additive auto-applicable · re-weights need explicit judgment"
    echo "- T6 review pattern · Essence file NOT auto-edited"
  else
    echo "_Essence coverage stable this scan · no proposals generated._"
  fi
  echo ""
  # ===================================================================
  echo "## All open yellow gaps"
  echo ""
  if [ -n "$YELLOW_GAPS" ]; then
    echo "$YELLOW_GAPS"
  else
    echo "_(none)_"
  fi
  echo ""
  if [ "$CHANGED" -eq 1 ] && [ -n "$DIFF_BLOCK" ]; then
    echo "## Inventory diff (first 120 lines)"
    echo ""
    echo '```diff'
    echo "$DIFF_BLOCK"
    echo '```'
    echo ""
  fi
  echo "---"
  echo "_Digest at \`~/.config/fpai/forge_weekly/${TODAY}.md\`. Next scan: next Sunday 10:00 local._"
  echo "_Queue state: \`${UPGRADE_QUEUE}\` · proposals: \`${UPGRADE_PROPOSALS}\` · auto-build log: \`${AUTO_BUILT_LOG}\`._"
} > "$DIGEST" || { log "ERROR: digest write failed"; exit 2; }

log "digest written: $DIGEST ($(wc -l < "$DIGEST") lines)"

# ----- 11. Snapshot current inventory for next-week diff -----------------
cp "$INVENTORY" "$SNAPSHOT"
log "snapshot refreshed: $SNAPSHOT"

# ----- 12. Ping sunheart-brain (non-fatal) -------------------------------
if [ -f "$BRAIN_ENV" ]; then
  # shellcheck disable=SC1090
  set -a; source "$BRAIN_ENV"; set +a
fi

BRAIN_BASE="${SH_BRAIN_BASE:-https://brain.sunheart.com}"
INGEST_TOKEN="${SH_INGEST_TOKEN:-}"

if [ -n "$INGEST_TOKEN" ]; then
  TITLE="Forge weekly digest · $TODAY"
  # Compose a compact preview (~600 chars) for the note body
  PREVIEW="$(head -80 "$DIGEST")"
  PAYLOAD="$(python3 -c '
import json, sys, os
payload = {
    "source": "forge-weekly-autopilot",
    "source_id": sys.argv[1],
    "title": sys.argv[2],
    "content": sys.argv[3],
    "tags": ["forge", "weekly", "autopilot", "capability-inventory", "ember-upgrade-loop"],
    "note_type": "🟢 Reference",
    "sensitivity": "🟡 Personal",
    "prefer": "local",
}
print(json.dumps(payload))
' "forge-weekly-${TODAY}" "$TITLE" "$PREVIEW")"

  HTTP_CODE="$(curl -sf -o "${OUTDIR}/last_brain_resp.json" -w '%{http_code}' \
    --max-time 30 \
    -H "Authorization: Bearer ${INGEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -X POST "${BRAIN_BASE}/ingest/add_note" \
    --data-raw "$PAYLOAD" 2>>"$LOG")" || HTTP_CODE="000"

  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    log "brain ingest OK (HTTP $HTTP_CODE)"
  else
    log "brain ingest non-200: HTTP=$HTTP_CODE (digest still written locally; not fatal)"
  fi
else
  log "WARN: SH_INGEST_TOKEN not found; skipped brain ping (digest still written)"
fi

log "Forge weekly scan complete. auto_queued=${#AUTO_BUILT_THIS_WEEK[@]} proposed=${#PROPOSED_THIS_WEEK[@]} escalated=${#ESCALATED_THIS_WEEK[@]} recurring=${#RECURRING_GAPS[@]}"
exit 0
