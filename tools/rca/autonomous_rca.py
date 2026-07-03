#!/usr/bin/env python3
"""Autonomous root-cause analysis — fires on error-class events, never lets the
same failure repeat unexamined.

James's directive 2026-07-03: "get to root cause analysis as an autonomous
function every time we spot an error in the logic or flow of the system."

The disease this treats: the system is built to swallow errors and keep running
(try/except-and-continue). That resilience became blindness — `diagnostic_error`
fired 96 times with the SAME import bug, swallowed every time, never root-caused.
Silent tolerance of a recurring error is the structural failure.

This tool:
  1. Reads the ops-ledger, groups error-class events by a NORMALIZED signature
     (strip timestamps / ids / line-numbers so the same bug collapses to one row).
  2. Flags a signature when it is NEW, or RECURRING past a threshold without a
     fix having landed — the 96x case would have screamed on the first recurrence.
  3. Runs a root-cause pass (claude -p, $0) on each flagged signature:
     symptom -> 5-whys -> ROOT -> BLAST RADIUS ("what else shares this root")
     -> proposed root-fix. The blast-radius step is the point: fix the class,
     not the instance.
  4. Writes findings + (optional) queues a root-fix decision into the build loop.

Incremental via a signature-seen store, so it analyzes each signature once (and
again only when it recurs past threshold). Cost-bounded: only flagged signatures
hit the LLM, capped per run. Reversible; dry-run by default.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_SEEN_STORE = Path(os.environ.get("RCA_SEEN_STORE", "/opt/fpai-build/.rca_seen.json"))
DEFAULT_FINDINGS = Path(os.environ.get("RCA_FINDINGS", "/opt/fpai-build/rca_findings.jsonl"))
_REPO = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_BUG_LOG = Path(os.environ.get("RCA_BUG_LOG", _REPO / "core" / "STATE" / "BUG_LOG.md"))
_BUG_LOG_SENTINEL = "<!-- RCA-APPEND-BELOW -->"

ERROR_TOKENS = (
    "error", "fail", "failed", "blocked", "revert", "conflict", "stall",
    "parse_fail", "circuit", "dead", "exception", "traceback", "missing",
    "denied", "timeout", "not found", "no such",
)

# Recurrence threshold: a signature seen this many times without a landed fix is
# flagged even if previously analyzed. 96x should never happen again.
DEFAULT_RECUR_THRESHOLD = int(os.environ.get("RCA_RECUR_THRESHOLD", "5"))
DEFAULT_MAX_ANALYZE = int(os.environ.get("RCA_MAX_ANALYZE", "4"))


def is_error_event(row: dict[str, Any]) -> bool:
    hay = f"{row.get('event','')} {row.get('detail','')}".lower()
    ev = str(row.get("event", "")).lower()
    if any(t in ev for t in ERROR_TOKENS):
        return True
    # detail-level errors even when event name is neutral
    return any(t in hay for t in ("traceback", "exception", "no such file", "cannot import", " denied"))


def normalize_signature(row: dict[str, Any]) -> str:
    """Collapse the same bug to one signature: drop timestamps, ids, line numbers,
    hex hashes, and digit runs so `d143`/`d144`/`SPEC_<uuid>` variants coalesce."""
    ev = str(row.get("event", "")).strip()
    detail = str(row.get("detail", "")).strip()
    text = f"{ev} | {detail}"
    text = re.sub(r"\b[0-9a-f]{8}-[0-9a-f-]{20,}\b", "<uuid>", text)  # uuids
    text = re.sub(r"\bd\d{2,4}\b", "d<N>", text)                       # dNNN
    text = re.sub(r"SPEC_\S+", "SPEC_<x>", text)                       # spec ids
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}[T \d:]*Z?\b", "<ts>", text)     # timestamps
    text = re.sub(r"line \d+", "line <n>", text)                        # line numbers
    text = re.sub(r"\b\d+\b", "<n>", text)                             # bare numbers
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200]


@dataclass
class Signature:
    signature: str
    count: int = 0
    first_ts: str = ""
    last_ts: str = ""
    loop: str = ""
    samples: list[str] = field(default_factory=list)


def group_errors(rows: list[dict[str, Any]]) -> dict[str, Signature]:
    groups: dict[str, Signature] = {}
    for row in rows:
        if not is_error_event(row):
            continue
        sig = normalize_signature(row)
        g = groups.get(sig)
        if g is None:
            g = Signature(signature=sig, loop=str(row.get("loop", "")))
            groups[sig] = g
        g.count += 1
        ts = str(row.get("ts", ""))
        if ts and not g.first_ts:
            g.first_ts = ts
        if ts:
            g.last_ts = ts
        detail = str(row.get("detail", "")).strip()
        if detail and len(g.samples) < 3 and detail not in g.samples:
            g.samples.append(detail[:200])
    return groups


def load_seen(path: Path) -> dict[str, int]:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_seen(path: Path, seen: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seen, indent=0))


def flag_signatures(
    groups: dict[str, Signature],
    seen: dict[str, int],
    *,
    recur_threshold: int = DEFAULT_RECUR_THRESHOLD,
) -> list[Signature]:
    """A signature is flagged if NEW (never analyzed) or RECURRING (analyzed but
    has fired recur_threshold+ more times since — meaning the fix didn't land)."""
    flagged = []
    for sig, g in groups.items():
        analyzed_at_count = seen.get(sig)
        if analyzed_at_count is None:
            flagged.append(g)
        elif g.count - analyzed_at_count >= recur_threshold:
            flagged.append(g)
    # worst offenders first
    flagged.sort(key=lambda s: s.count, reverse=True)
    return flagged


RCA_PROMPT = """You are the autonomous root-cause analyst for a self-building AI system.
A recurring error signature was detected. Do NOT propose a patch for the symptom.
Find the ROOT and its BLAST RADIUS.

ERROR SIGNATURE (normalized): {signature}
TIMES SEEN: {count}  (first {first_ts}, last {last_ts}, loop={loop})
SAMPLE DETAILS:
{samples}

Respond with ONLY a JSON object:
{{"symptom":"one line","five_whys":["why1","why2","..."],"root_cause":"the underlying invariant/assumption that was violated","blast_radius":"what OTHER parts of the system share this same root and could fail the same way","root_fix":"the change that fixes the CLASS, not this instance","severity":"low|med|high","confidence":"low|med|high"}}"""


def _resolve_claude() -> str | None:
    for cand in (os.environ.get("CLAUDE_BIN"), "claude",
                 "/root/.local/bin/claude", "/usr/local/bin/claude"):
        if not cand:
            continue
        try:
            if subprocess.run(["which", cand] if "/" not in cand else ["test", "-x", cand],
                              capture_output=True).returncode == 0:
                return cand
        except Exception:
            continue
    return None


def analyze_signature(sig: Signature, *, runner: Callable | None = None) -> dict[str, Any]:
    prompt = RCA_PROMPT.format(
        signature=sig.signature, count=sig.count, first_ts=sig.first_ts,
        last_ts=sig.last_ts, loop=sig.loop, samples="\n".join(f"- {s}" for s in sig.samples),
    )
    claude = _resolve_claude()
    if not claude and runner is None:
        return {"status": "skipped", "reason": "claude binary not found"}
    run = runner or subprocess.run
    try:
        r = run([claude, "-p", "--effort", "high", prompt],
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
        txt = (r.stdout or "").strip()
        start, end = txt.find("{"), txt.rfind("}")
        if start >= 0 and end > start:
            return {"status": "ok", "analysis": json.loads(txt[start:end + 1])}
        return {"status": "error", "reason": "no JSON in response", "raw": txt[:300]}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)[:200]}


def _append_bug_log(bug_log: Path, sig: Signature, analysis: dict[str, Any]) -> None:
    """Insert one confirmed root as a markdown row after the sentinel in BUG_LOG.md,
    closing the loop error -> RCA -> BUG_LOG. Idempotent: skips if the signature is
    already present. Never raises."""
    try:
        from datetime import datetime, timezone
        import hashlib
        text = bug_log.read_text(encoding="utf-8")
        if _BUG_LOG_SENTINEL not in text:
            return
        marker = "sig:" + hashlib.sha1(sig.signature.encode()).hexdigest()[:10]
        if marker in text:  # already logged this root (stable, row-embedded)
            return
        def _cell(s: str, n: int = 150) -> str:
            return str(s or "").replace("|", "\\|").replace("\n", " ")[:n]
        detected = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = (
            f"| {detected} | {sig.count}x | {_cell(sig.loop, 16)} | "
            f"{_cell(analysis.get('root_cause'), 160)} | {_cell(analysis.get('root_fix'), 140)} | "
            f"{_cell(analysis.get('severity'), 6)}/{_cell(analysis.get('confidence'), 6)} <!-- {marker} --> |"
        )
        text = text.replace(_BUG_LOG_SENTINEL, _BUG_LOG_SENTINEL + "\n" + row, 1)
        bug_log.write_text(text, encoding="utf-8")
    except Exception:
        pass


def _surface_to_ledger(ops_ledger: Path, sig: Signature, analysis: dict[str, Any]) -> None:
    """Append one rca_finding event so the root cause enters the existing bus
    (ops_ledger -> HOT_STATE -> digest). One line per root, NOT per symptom —
    the 96x import error surfaces once, as its root, not 96 times."""
    try:
        from datetime import datetime, timezone
        row = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "loop": "rca",
            "event": "rca_finding",
            "detail": f"[{analysis.get('severity','?')}] {sig.count}x {sig.loop}: {str(analysis.get('root_cause',''))[:180]}",
            "cost": "$0",
            "artifact": str(analysis.get("root_fix", ""))[:200],
            "next": f"blast: {str(analysis.get('blast_radius',''))[:160]}",
        }
        with ops_ledger.open("a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


def run_rca(
    *,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    seen_store: Path = DEFAULT_SEEN_STORE,
    findings_path: Path = DEFAULT_FINDINGS,
    bug_log: Path = DEFAULT_BUG_LOG,
    recur_threshold: int = DEFAULT_RECUR_THRESHOLD,
    max_analyze: int = DEFAULT_MAX_ANALYZE,
    dry_run: bool = True,
    runner: Callable | None = None,
) -> dict[str, Any]:
    rows = []
    try:
        for line in ops_ledger.read_text(errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return {"ok": False, "reason": f"cannot read {ops_ledger}"}

    groups = group_errors(rows)
    seen = load_seen(seen_store)
    flagged = flag_signatures(groups, seen, recur_threshold=recur_threshold)
    to_analyze = flagged[:max_analyze]

    findings = []
    for g in to_analyze:
        result = analyze_signature(g, runner=runner) if not dry_run else {"status": "dry_run"}
        finding = {
            "signature": g.signature, "count": g.count,
            "first_ts": g.first_ts, "last_ts": g.last_ts, "loop": g.loop,
            "samples": g.samples, "result": result,
        }
        findings.append(finding)
        if not dry_run and result.get("status") == "ok":
            seen[g.signature] = g.count  # mark analyzed at this count
            with findings_path.open("a") as f:
                f.write(json.dumps(finding) + "\n")
            _surface_to_ledger(ops_ledger, g, result.get("analysis", {}))
            _append_bug_log(bug_log, g, result.get("analysis", {}))

    if not dry_run:
        save_seen(seen_store, seen)

    return {
        "ok": True,
        "total_error_signatures": len(groups),
        "flagged": len(flagged),
        "analyzed": len(to_analyze),
        "dry_run": dry_run,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    ap.add_argument("--seen-store", type=Path, default=DEFAULT_SEEN_STORE)
    ap.add_argument("--findings", type=Path, default=DEFAULT_FINDINGS)
    ap.add_argument("--recur-threshold", type=int, default=DEFAULT_RECUR_THRESHOLD)
    ap.add_argument("--max-analyze", type=int, default=DEFAULT_MAX_ANALYZE)
    ap.add_argument("--execute", action="store_true", help="Run the LLM RCA + persist (default: detect-only dry run).")
    args = ap.parse_args(argv)
    result = run_rca(
        ops_ledger=args.ops_ledger, seen_store=args.seen_store, findings_path=args.findings,
        recur_threshold=args.recur_threshold, max_analyze=args.max_analyze, dry_run=not args.execute,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
