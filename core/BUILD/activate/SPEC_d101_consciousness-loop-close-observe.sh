#!/usr/bin/env bash
# Activate d101 consciousness-loop closeout wiring.
set -euo pipefail

REPO_ROOT="${FPAI_CODEX_REPO:-/opt/fpai-build/FPAI_Cockpit}"
HOOK_BLOCK='
# d101 consciousness observer (detached, private, never blocks settle)
CONSCIOUSNESS_OBSERVER="$REPO_ROOT/tools/consciousness/run_observer.sh"
if [ -x "$CONSCIOUSNESS_OBSERVER" ]; then
  ( nohup bash "$CONSCIOUSNESS_OBSERVER" "$EPISODIC_PATH" "$SESSION_ID" > "$LOG_DIR/${SESSION_ID}.consciousness.log" 2>&1 & ) >/dev/null 2>&1
  log "consciousness_observer_dispatched"
fi
'

patch_hook() {
  local hook="$1"
  if [ ! -f "$hook" ]; then
    echo "skip missing hook: $hook"
    return 0
  fi
  if grep -q "d101 consciousness observer" "$hook"; then
    echo "already patched: $hook"
    return 0
  fi
  python3 - "$hook" "$HOOK_BLOCK" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
block = sys.argv[2].rstrip() + "\n\n"
text = path.read_text(encoding="utf-8")
needle = "# -- Background mirror sync"
idx = text.find(needle)
if idx < 0:
    needle = "SYNC_SCRIPT="
    idx = text.find(needle)
if idx < 0:
    raise SystemExit(f"could not find sync insertion point in {path}")
path.write_text(text[:idx] + block + text[idx:], encoding="utf-8")
PY
  echo "patched: $hook"
}

patch_hook "$REPO_ROOT/.claude/hooks/auto-settle.sh"
patch_hook "$REPO_ROOT/.codex/hooks/auto-settle.sh"

