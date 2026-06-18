#!/usr/bin/env bash
# Pre-build Forge scout.
#
# Reads a build spec before Codex runs, asks The Forge for existing resources,
# libraries, and best-practice alternatives, appends a bounded report to the
# spec, and writes an append-only JSONL scout log. Failures are non-blocking.
set -u

SPEC_FILE="${1:-}"
[ -z "$SPEC_FILE" ] && { echo "usage: forge_scout.sh <spec-file>" >&2; exit 2; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEC_PATH="$SPEC_FILE"
case "$SPEC_PATH" in
  /*) ;;
  *) SPEC_PATH="$PWD/$SPEC_PATH" ;;
esac

LOG_PATH="${FORGE_SCOUT_LOG:-$ROOT/tools/build_loop/scout_log.jsonl}"
TIMEOUT_SECONDS="${FORGE_SCOUT_TIMEOUT_SECONDS:-30}"
CLAUDE_CMD="${FORGE_SCOUT_CMD:-claude -p}"
MARKER="## Forge Scout Report"

if [ "${FORGE_SCOUT_DISABLE:-0}" = "1" ] || [ "${FORGE_SCOUT_ENABLED:-1}" = "0" ]; then
  echo "forge scout skipped"
  exit 0
fi

if [ ! -f "$SPEC_PATH" ]; then
  echo "forge scout: missing spec: $SPEC_FILE" >&2
  exit 0
fi

if grep -Fq "$MARKER" "$SPEC_PATH"; then
  echo "forge scout: report already present for $(basename "$SPEC_PATH")"
  exit 0
fi

SPEC_ID="$(basename "$SPEC_PATH" .md)"
RESOURCE_INVENTORY="$ROOT/core/STATE/RESOURCE_INVENTORY.md"
AVAILABLE_RESOURCES="$ROOT/core/STATE/AVAILABLE_RESOURCES.md"
TOOL_SCOUT_REPORT="$ROOT/core/BUILD/signals/tool_scout_report.md"
TOOL_SCOUT_PROPOSALS="$ROOT/core/BUILD/signals/tool_scout_proposals.jsonl"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/fpai-forge-scout.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

context_file="$tmpdir/context.md"
{
  echo "# Spec"
  sed -n '1,260p' "$SPEC_PATH"
  echo
  echo "# Resource Inventory"
  if [ -f "$RESOURCE_INVENTORY" ]; then
    sed -n '1,260p' "$RESOURCE_INVENTORY"
  else
    echo "(missing core/STATE/RESOURCE_INVENTORY.md)"
  fi
  echo
  echo "# Available Resources"
  if [ -f "$AVAILABLE_RESOURCES" ]; then
    sed -n '1,220p' "$AVAILABLE_RESOURCES"
  else
    echo "(missing core/STATE/AVAILABLE_RESOURCES.md)"
  fi
  echo
  echo "# Tool Scout Report"
  if [ -f "$TOOL_SCOUT_REPORT" ]; then
    sed -n '1,180p' "$TOOL_SCOUT_REPORT"
  else
    echo "(missing core/BUILD/signals/tool_scout_report.md)"
  fi
  echo
  echo "# Tool Scout Proposals"
  if [ -f "$TOOL_SCOUT_PROPOSALS" ]; then
    tail -n 20 "$TOOL_SCOUT_PROPOSALS"
  else
    echo "(missing core/BUILD/signals/tool_scout_proposals.jsonl)"
  fi
} > "$context_file"

prompt_file="$tmpdir/prompt.md"
cat > "$prompt_file" <<'EOF'
You are The Forge — pre-build scout for FPAI_Cockpit.

Read the spec and local evidence below. Before Codex builds, identify whether
the work should reuse an existing repo tool, installed resource, known package,
or best-practice approach instead of building blindly from scratch.

Rules:
- Do not install, deploy, spend money, read secrets, send outreach, or make live changes.
- If external search/web tools are available in this non-interactive scout pass, use them only for public package/project facts. Otherwise rely on the supplied local evidence.
- Be concrete and concise, under 200 words.
- Format exactly:
EXISTING: ...
LIBRARY: ...
BEST_PRACTICE: ...
SAVE: ...

Local evidence follows.
EOF
cat "$context_file" >> "$prompt_file"

report_file="$tmpdir/report.txt"
status="ok"
if command -v timeout >/dev/null 2>&1; then
  timeout "$TIMEOUT_SECONDS" bash -c "$CLAUDE_CMD" < "$prompt_file" > "$report_file" 2>"$tmpdir/stderr" || status="failed"
else
  bash -c "$CLAUDE_CMD" < "$prompt_file" > "$report_file" 2>"$tmpdir/stderr" || status="failed"
fi

if [ "$status" != "ok" ] || [ ! -s "$report_file" ]; then
  echo "forge scout failed for $SPEC_ID; continuing" >&2
  python3 - "$LOG_PATH" "$SPEC_ID" "$status" "" "" "" <<'PY' || true
import datetime as dt, json, pathlib, sys
path, spec_id, status, existing, library, save = sys.argv[1:7]
row = {
    "timestamp": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "spec_id": spec_id,
    "status": status,
    "existing_found": False,
    "library_found": False,
    "estimated_time_saved": "",
    "cost": "$0 marginal",
}
pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
with open(path, "a", encoding="utf-8") as handle:
    handle.write(json.dumps(row, sort_keys=True) + "\n")
PY
  exit 0
fi

python3 - "$SPEC_PATH" "$LOG_PATH" "$SPEC_ID" "$report_file" <<'PY'
import datetime as dt
import json
import pathlib
import re
import sys

spec_path = pathlib.Path(sys.argv[1])
log_path = pathlib.Path(sys.argv[2])
spec_id = sys.argv[3]
report_path = pathlib.Path(sys.argv[4])
raw = report_path.read_text(encoding="utf-8", errors="replace")
lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
bounded = "\n".join(lines)[:1600].strip()
if not bounded:
    raise SystemExit(0)

def field(name: str) -> str:
    match = re.search(rf"^{name}:\s*(.+)$", bounded, flags=re.I | re.M)
    return match.group(1).strip() if match else ""

existing = field("EXISTING")
library = field("LIBRARY")
save = field("SAVE")
existing_found = bool(existing and existing.lower() not in {"none", "n/a", "no"})
library_found = bool(library and library.lower() not in {"none", "n/a", "no"})

with spec_path.open("a", encoding="utf-8") as handle:
    handle.write("\n\n## Forge Scout Report\n")
    handle.write(f"_Generated: {dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')} · pre-build scout · non-blocking_\n\n")
    handle.write(bounded)
    handle.write("\n")

row = {
    "timestamp": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "spec_id": spec_id,
    "status": "ok",
    "existing_found": existing_found,
    "library_found": library_found,
    "estimated_time_saved": save,
    "best_practice": field("BEST_PRACTICE"),
    "library": library,
    "cost": "$0 marginal",
}
log_path.parent.mkdir(parents=True, exist_ok=True)
with log_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(row, sort_keys=True) + "\n")
PY

echo "forge scout appended report for $SPEC_ID"
