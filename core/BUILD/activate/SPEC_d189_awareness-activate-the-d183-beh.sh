#!/usr/bin/env bash
# Activate d183's behavioral awareness probe as the live signal writer.
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
LIVE="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
SERVICE_NAME="fpai-awareness-reliability.service"
TIMER_NAME="fpai-awareness-reliability.timer"
SERVICE_SRC="$REPO/core/BUILD/cron/$SERVICE_NAME"
TIMER_SRC="$REPO/core/BUILD/cron/$TIMER_NAME"
RUNNER="$REPO/core/BUILD/cron/fpai-awareness-reliability-run.sh"
PROBE="$REPO/tools/awareness/reliability_probe.py"
SIGNAL_JSON="$REPO/core/BUILD/signals/awareness_reliability.json"
SIGNAL_MD="$REPO/core/BUILD/signals/awareness_reliability.md"
OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}"
COOLDOWN_FILE="${AWARENESS_RELIABILITY_COOLDOWN_FILE:-/opt/fpai-build/.awareness_reliability_last_alert}"
PYTHON_BIN="$LIVE/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="/usr/bin/python3"
fi

for path in "$SERVICE_SRC" "$TIMER_SRC" "$RUNNER" "$PROBE" "$REPO/tools/awareness/verify_awareness.py"; do
  if [ ! -f "$path" ]; then
    echo "d189 activation failed: missing required file $path" >&2
    exit 1
  fi
done

"$PYTHON_BIN" -m py_compile "$PROBE" "$REPO/tools/awareness/verify_awareness.py"
bash -n "$RUNNER"
chmod +x "$RUNNER"

install -m 0644 "$SERVICE_SRC" "$SYSTEMD_DIR/$SERVICE_NAME"
install -m 0644 "$TIMER_SRC" "$SYSTEMD_DIR/$TIMER_NAME"
systemctl daemon-reload
systemctl enable --now "$TIMER_NAME"

set +e
"$PYTHON_BIN" "$PROBE" \
  --ops-ledger "$OPS_LEDGER" \
  --json-path "$SIGNAL_JSON" \
  --markdown-path "$SIGNAL_MD" \
  --cooldown-file "$COOLDOWN_FILE" \
  --source d189-activation \
  --threshold 0.95 \
  --json
probe_rc=$?
set -e

"$PYTHON_BIN" - "$SIGNAL_JSON" "$probe_rc" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
probe_rc = int(sys.argv[2])
if not path.exists():
    raise SystemExit(f"d189 activation failed: missing report {path}")

report = json.loads(path.read_text(encoding="utf-8"))
metric = report.get("metric") or {}
reason = str(metric.get("reason") or "")
question = str(metric.get("question") or "")
answer = str(metric.get("answer") or "")
behavioral_pass = metric.get("behavioral_pass")
context_render = metric.get("context_render_continuity")

errors = []
if report.get("primary_metric") != "behavioral_bot_answer":
    errors.append("primary_metric is not behavioral_bot_answer")
if report.get("secondary_signal") != "context_render_continuity":
    errors.append("secondary_signal is not context_render_continuity")
if behavioral_pass is not True and behavioral_pass is not False:
    errors.append("behavioral_pass is not a boolean")
if context_render is not True and context_render is not False:
    errors.append("context_render_continuity is not a boolean")
if not question:
    errors.append("probe did not derive a live latest-insight question")
if not answer:
    errors.append("probe did not receive a bot answer to grade")
if "latest title missing from bot context" in reason:
    errors.append("primary reason still reflects the retired context-render title proxy")
if "bot answer did not match latest session insight" in reason:
    errors.append("primary reason still uses the retired ambiguous d183 wording")
if probe_rc not in (0, 1):
    errors.append(f"probe exited with unexpected code {probe_rc}")

if errors:
    raise SystemExit("d189 activation failed: " + "; ".join(errors))

print(
    "d189 activation smoke: behavioral_pass=%s context_render_continuity=%s reason=%s"
    % (behavioral_pass, context_render, reason or "ok")
)
PY

echo "d189 activation complete: behavioral awareness probe is installed, timer enabled, and live signal smoke-tested"
