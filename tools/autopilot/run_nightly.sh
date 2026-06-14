#!/usr/bin/env bash
# Nightly autopilot orchestrator wrapper · MVP v1 · 2026-05-24
# Spec: ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/spec_autopilot_cron_light.md
set -euo pipefail

# === Pilot window guard ===
PILOT_START="2026-05-23"
PILOT_END="2026-06-30"  # extended past initial Mon-Wed for ongoing pilot
TODAY="$(date +%Y-%m-%d)"
if [[ "$TODAY" < "$PILOT_START" ]] || [[ "$TODAY" > "$PILOT_END" ]]; then
  echo "[$(date -Iseconds)] outside pilot window ($PILOT_START..$PILOT_END), exiting"
  exit 0
fi

# === Kill switch ===
if [[ -f "$HOME/.config/fpai/autopilot/.disabled" ]]; then
  echo "[$(date -Iseconds)] autopilot DISABLED via .disabled flag, exiting"
  exit 0
fi

# === Defaults ===
MODEL="${AUTOPILOT_MODEL:-claude-opus-4-7}"
TASK=""
BUDGET="${AUTOPILOT_BUDGET_USD:-5.00}"
DRY_RUN=false
MANUAL_NOW=false

# === Flag parsing ===
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --manual-now) MANUAL_NOW=true; shift ;;
    --task=*) TASK="${1#*=}"; shift ;;
    --model=*) MODEL="${1#*=}"; shift ;;
    --budget-usd=*) BUDGET="${1#*=}"; shift ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

# === Auto-select model by date (cron mode only) ===
if ! $MANUAL_NOW && [[ -z "${AUTOPILOT_MODEL:-}" ]]; then
  case "$TODAY" in
    2026-05-23|2026-05-24|2026-05-25|2026-05-26) MODEL="claude-opus-4-7" ;;
    2026-05-27|2026-05-28|2026-05-29|2026-05-30) MODEL="qwen3.7-max" ;;
  esac
fi

# === Exports for orchestrator ===
export AUTOPILOT_MODEL="$MODEL"
export AUTOPILOT_DATE="$TODAY"
export AUTOPILOT_BUDGET_USD="$BUDGET"
export AUTOPILOT_RUN_DIR="$HOME/.config/fpai/autopilot"

# === Path setup for cron (cron has minimal PATH) ===
# CRITICAL: $HOME/.local/bin FIRST · /usr/local/bin has stale claude binary that lacks --model flag
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# === Locate orchestrator ===
ORCHESTRATOR_DIR="$(cd "$(dirname "$0")" && pwd)"
ORCHESTRATOR="$ORCHESTRATOR_DIR/orchestrate.py"

if [[ ! -f "$ORCHESTRATOR" ]]; then
  echo "FATAL: orchestrator not found at $ORCHESTRATOR" >&2
  exit 1
fi

# === Build args ===
ARGS=(--model "$MODEL" --date "$TODAY" --budget-usd "$BUDGET")
if [[ -n "$TASK" ]]; then ARGS+=(--task "$TASK"); fi
if $DRY_RUN; then ARGS+=(--dry-run); fi

# Reversibility flags (always on per Trust-tier 4.1)
ARGS+=(--reversible-only --no-git-push --no-identity-writes --no-treasury --no-publish)

echo "[$(date -Iseconds)] dispatching orchestrator: model=$MODEL date=$TODAY budget=\$$BUDGET dry_run=$DRY_RUN task=${TASK:-<auto>}"

# Execute
exec python3 "$ORCHESTRATOR" "${ARGS[@]}"
