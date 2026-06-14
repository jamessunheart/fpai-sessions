#!/usr/bin/env bash
# Stop hook — SI-1 live cost meter.
#
# On every Stop (end of an assistant response turn), reads the session
# transcript, sums token usage from any assistant messages NOT yet counted
# (tracked via a per-session line cursor), computes a shadow est_usd per
# model from rates.json, and appends rows to the cost ledger.
#
# IMPORTANT honesty notes:
#  - Claude Max is flat-rate. est_usd here is the API-EQUIVALENT shadow cost
#    (what these tokens WOULD cost on metered API), not real billed dollars.
#    It is the right number for routing/cost-awareness, not for invoices.
#  - Task SUBAGENT token usage writes to sidechain transcripts under the
#    current session directory. This hook now scans those transcripts with
#    per-file cursors so subagent fan-outs are counted once.
#
# Disable: touch ~/.config/fpai/cost/.disabled   (re-enable: rm it)

set -u

COST_DIR="$HOME/.config/fpai/cost"
LEDGER="$COST_DIR/ledger.jsonl"
RATES="$COST_DIR/rates.json"
CURSOR_DIR="$COST_DIR/cursors"

# Kill switch — always exit clean so we never block the session.
[ -f "$COST_DIR/.disabled" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

INPUT=$(cat)
TRANSCRIPT=$(printf '%s' "$INPUT" | python3 -c 'import json,sys;
try: print(json.load(sys.stdin).get("transcript_path",""))
except: print("")' 2>/dev/null)
SESSION_ID=$(printf '%s' "$INPUT" | python3 -c 'import json,sys;
try: print(json.load(sys.stdin).get("session_id","unknown"))
except: print("unknown")' 2>/dev/null)

[ -z "$TRANSCRIPT" ] && exit 0
[ -f "$TRANSCRIPT" ] || exit 0
mkdir -p "$CURSOR_DIR" 2>/dev/null

CURSOR_FILE="$CURSOR_DIR/$SESSION_ID.cursor"
SUBAGENT_CURSOR_DIR="$CURSOR_DIR/subagents"
mkdir -p "$SUBAGENT_CURSOR_DIR" 2>/dev/null

python3 - "$TRANSCRIPT" "$SESSION_ID" "$RATES" "$LEDGER" "$CURSOR_FILE" "$SUBAGENT_CURSOR_DIR" <<'PY'
import json, sys, os, datetime, glob, hashlib

transcript, session, rates_path, ledger, cursor_file, subagent_cursor_dir = sys.argv[1:7]

# Load rates
try:
    rates = json.load(open(rates_path))["rates"]
except Exception:
    rates = {"_default": {"in":5.0,"out":15.0,"cache_read":0.5,"cache_write":6.25}}

# Resume cursor (number of transcript lines already counted)
start = 0
try:
    start = int(open(cursor_file).read().strip())
except Exception:
    start = 0

def rate_for(model):
    if not model:
        return rates.get("_default")
    if model in rates:
        return rates[model]
    # prefix match (e.g. claude-opus-4-8-... )
    for k, v in rates.items():
        if k != "_default" and model.startswith(k):
            return v
    return rates.get("_default")

def add_usage(agg, model, usage):
    if not usage:
        return
    a = agg.setdefault(model or "", {"in":0,"out":0,"cr":0,"cw":0})
    a["in"]  += int(usage.get("input_tokens", 0) or 0)
    a["out"] += int(usage.get("output_tokens", 0) or 0)
    a["cr"]  += int(usage.get("cache_read_input_tokens", 0) or 0)
    a["cw"]  += int(usage.get("cache_creation_input_tokens", 0) or 0)

def scan_transcript(path, start, require_sidechain=False):
    agg = {}   # model -> token sums
    total_lines = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            total_lines = i + 1
            if i < start:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if require_sidechain and not o.get("isSidechain"):
                continue
            msg = o.get("message", {})
            if msg.get("role") != "assistant":
                continue
            add_usage(agg, msg.get("model", ""), msg.get("usage"))
    return agg, total_lines

def cursor_for_subagent(path):
    stem = hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]
    return os.path.join(subagent_cursor_dir, stem + ".cursor")

def subagent_paths_for(path):
    # Claude Code stores sidechain transcripts next to the parent session:
    #   <project>/<session-id>.jsonl
    #   <project>/<session-id>/subagents/agent-*.jsonl
    base = path[:-6] if path.endswith(".jsonl") else os.path.splitext(path)[0]
    return sorted(glob.glob(os.path.join(base, "subagents", "*.jsonl")))

agg, total_lines = scan_transcript(transcript, start)

subagent_rows = []
for sub_path in subagent_paths_for(transcript):
    sub_cursor = cursor_for_subagent(sub_path)
    sub_start = 0
    try:
        sub_start = int(open(sub_cursor).read().strip())
    except Exception:
        sub_start = 0
    try:
        sub_agg, sub_total_lines = scan_transcript(sub_path, sub_start, require_sidechain=True)
    except Exception:
        continue
    if not sub_agg:
        try:
            open(sub_cursor, "w").write(str(sub_total_lines))
        except Exception:
            pass
        continue
    agent_id = os.path.basename(sub_path).removesuffix(".jsonl")
    subagent_rows.append((sub_path, sub_cursor, sub_total_lines, agent_id, sub_agg))

# Nothing new
if not agg and not subagent_rows:
    open(cursor_file, "w").write(str(total_lines))
    sys.exit(0)

ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

def rows_from_agg(label, source, agg, extra=None):
    rows = []
    for model, a in agg.items():
        r = rate_for(model)
        est = (a["in"]*r["in"] + a["out"]*r["out"]
               + a["cr"]*r.get("cache_read", r["in"]*0.1)
               + a["cw"]*r.get("cache_write", r["in"]*1.25)) / 1_000_000.0
        row = {
            "timestamp": ts,
            "label": label,
            "model": model or "unknown",
            "input_tokens": a["in"],
            "output_tokens": a["out"],
            "cache_read_tokens": a["cr"],
            "cache_write_tokens": a["cw"],
            "est_usd": round(est, 6),
            "session": session,
            "source": source,
            "billing": "max-flat-shadow" if (model or "").startswith("claude") else "metered-estimate",
        }
        if extra:
            row.update(extra)
        rows.append(row)
    return rows

rows = rows_from_agg("session-turn", "stop-hook", agg)
for sub_path, sub_cursor, sub_total_lines, agent_id, sub_agg in subagent_rows:
    rows.extend(rows_from_agg(
        "subagent-turn",
        "stop-hook-subagent",
        sub_agg,
        {"agent": agent_id, "transcript": sub_path},
    ))

os.makedirs(os.path.dirname(ledger), exist_ok=True)
with open(ledger, "a", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")

open(cursor_file, "w").write(str(total_lines))
for sub_path, sub_cursor, sub_total_lines, agent_id, sub_agg in subagent_rows:
    try:
        open(sub_cursor, "w").write(str(sub_total_lines))
    except Exception:
        pass
PY

exit 0
