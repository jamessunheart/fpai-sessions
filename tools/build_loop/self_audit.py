#!/usr/bin/env python3
"""Idle-triggered self-audit for the build loop.

The audit is a proposal generator only. It reads local operational signals,
asks the local Claude CLI for 1-3 improvement specs, validates the JSON, and
returns the sanitized list to the caller. Queueing remains the shell loop's job.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from tools.intelligence.model_router import call_model
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_LAST_AUDIT = Path(os.environ.get("SELF_AUDIT_LAST_FILE", "/opt/fpai-build/.last_audit_date"))
DEFAULT_MERGED_COUNTER = Path(os.environ.get("SELF_AUDIT_MERGED_COUNTER", "/opt/fpai-build/.merged_since_audit"))
DEFAULT_REVIEWS_DIR = REPO_ROOT / "core" / "BUILD" / "reviews"
DEFAULT_GAPS_FILE = REPO_ROOT / "core" / "BUILD" / "ARCHITECTURE_GAPS.md"
KEY_SERVICES = [
    "fpai-build-loop",
    "fpai-morning-digest",
    "sh-brain-tgbot",
    "sh-brain-index",
    "sh-mcp-http",
]
MAX_SPECS = 3
TITLE_LIMIT = 60
RISK_CLASSES = {"low", "med"}
FORBIDDEN_RE = re.compile(
    r"\b("
    r"money|treasury|payment|payroll|wire|wallet|identity|passport|kyc|"
    r"production\s+deploy|prod[- ]?irreversible|irreversible|delete|archive|"
    r"secret|credential|outreach|send\s+(email|message|dm)"
    r")\b",
    re.IGNORECASE,
)

log = logging.getLogger("self_audit")


@dataclass(frozen=True)
class TriggerDecision:
    should_run: bool
    trigger: str | None
    reason: str
    age_hours: float | None
    merged_since_audit: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_audit_stamp(text: str | None) -> datetime | None:
    if not text:
        return None
    value = text.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d-%H", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def read_text(path: Path, limit: int = 120_000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return data[-limit:]


def read_jsonl(path: Path, *, since: datetime | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if since:
            ts = parse_row_time(row)
            if ts and ts < since:
                continue
        rows.append(row)
    return rows


def parse_row_time(row: dict[str, Any]) -> datetime | None:
    raw = str(row.get("ts") or row.get("timestamp") or row.get("created_at") or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def collect_ops_summary(path: Path = DEFAULT_OPS_LEDGER, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or utc_now()
    rows = read_jsonl(path, since=current - timedelta(days=7))
    events = Counter(str(r.get("event") or r.get("type") or "unknown") for r in rows)
    failures = [
        compact(" ".join(str(r.get(k, "")) for k in ("loop", "event", "detail", "next")))
        for r in rows
        if str(r.get("event") or r.get("type")).lower() in {"failed", "error", "warning", "skipped"}
    ]
    merged = sum(1 for r in rows if str(r.get("event") or r.get("type")).lower() == "merged")
    rejected = sum(1 for r in rows if "reject" in json.dumps(r).lower() or "request_changes" in json.dumps(r).lower())
    silent = sum(1 for r in rows if str(r.get("event") or r.get("type")).lower() in {"ran", "skipped"} and not r.get("next"))
    return {
        "path": str(path),
        "rows": len(rows),
        "by_event": dict(events.most_common()),
        "failures": failures[-12:],
        "merged_count": merged,
        "rejected_or_request_changes_count": rejected,
        "silent_or_no_work_count": silent,
    }


def collect_review_patterns(reviews_dir: Path = DEFAULT_REVIEWS_DIR) -> dict[str, Any]:
    if not reviews_dir.exists():
        return {"path": str(reviews_dir), "files": 0, "request_changes": 0, "patterns": []}
    texts = []
    for path in sorted(reviews_dir.glob("*.md"))[-40:]:
        text = read_text(path, limit=20_000)
        if "REQUEST_CHANGES" in text or "request changes" in text.lower():
            texts.append((path.name, text))
    phrases: Counter[str] = Counter()
    for _name, text in texts:
        for line in text.splitlines():
            lower = line.lower()
            if any(marker in lower for marker in ("request_changes", "bug", "risk", "missing", "failure", "test")):
                cleaned = compact(line.lstrip("#-* >` ").strip())
                if 12 <= len(cleaned) <= 180:
                    phrases[cleaned] += 1
    return {
        "path": str(reviews_dir),
        "files": len(list(reviews_dir.glob("*.md"))),
        "request_changes": len(texts),
        "patterns": [{"text": text, "count": count} for text, count in phrases.most_common(10)],
    }


def collect_architecture_gaps(path: Path = DEFAULT_GAPS_FILE) -> dict[str, Any]:
    text = read_text(path, limit=60_000)
    partial = []
    for line in text.splitlines():
        if "PARTIAL" in line.upper() or "gap" in line.lower():
            cleaned = compact(line.strip(" -#\t"))
            if cleaned:
                partial.append(cleaned[:220])
    return {"path": str(path), "partial_or_gap_lines": partial[:20]}


def collect_brain_index_summary() -> dict[str, Any]:
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return {"available": False, "reason": "missing local DB DSN"}
    try:
        import psycopg  # type: ignore
    except ImportError:
        return {"available": False, "reason": "psycopg unavailable"}
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            return {
                "available": True,
                "decisions": query_decision_summary(conn),
                "corrections": query_correction_summary(conn),
            }
    except Exception as exc:  # pragma: no cover - depends on live host DB
        return {"available": False, "reason": f"read failed: {exc}"}


def query_decision_summary(conn: Any) -> dict[str, Any]:
    sql = """
        SELECT
          COUNT(*) FILTER (
            WHERE lower(COALESCE(status::text, state::text, '')) = 'answered'
              AND COALESCE(needs_build, false)
              AND NOT COALESCE(spec_written, false)
          ) AS answered_unbuilt,
          COUNT(*) FILTER (WHERE COALESCE(confidence, 0) >= 0.8 AND COALESCE(override, false)) AS high_confidence_overrides,
          COUNT(*) FILTER (WHERE lower(COALESCE(status::text, state::text, '')) IN ('reversed', 'superseded')) AS reversals
        FROM brain_index.decisions
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone() or (0, 0, 0)
        return {
            "answered_needs_build_unbuilt": int(row[0] or 0),
            "high_confidence_overrides": int(row[1] or 0),
            "reversal_patterns": int(row[2] or 0),
        }
    except Exception as exc:
        return {"error": str(exc)}


def query_correction_summary(conn: Any) -> dict[str, Any]:
    sql = """
        SELECT COALESCE(topic, correction_type, 'unknown')::text AS topic, COUNT(*)::int
          FROM brain_index.corrections
         WHERE COALESCE(captured_at, created_at, NOW()) > NOW() - INTERVAL '7 days'
         GROUP BY 1
         ORDER BY 2 DESC
         LIMIT 12
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        return {"top_topics": [{"topic": str(topic), "count": int(count)} for topic, count in rows]}
    except Exception as exc:
        return {"error": str(exc)}


def collect_service_status(services: Iterable[str] = KEY_SERVICES) -> dict[str, Any]:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return {"available": False, "reason": "systemctl not found", "services": []}
    out = []
    for service in services:
        try:
            result = subprocess.run(
                [systemctl, "status", service, "--no-pager"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=5,
            )
            text = compact(result.stdout)
            state = "active" if "Active: active" in text else "degraded"
            out.append({"name": service, "state": state, "status": text[:600]})
        except Exception as exc:
            out.append({"name": service, "state": "unknown", "status": str(exc)})
    return {"available": True, "services": out}


def build_audit_context(
    *,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    reviews_dir: Path = DEFAULT_REVIEWS_DIR,
    gaps_file: Path = DEFAULT_GAPS_FILE,
    now: datetime | None = None,
) -> dict[str, Any]:
    return {
        "generated_at": (now or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ops_ledger_7d": collect_ops_summary(ops_ledger, now=now),
        "review_patterns": collect_review_patterns(reviews_dir),
        "brain_index": collect_brain_index_summary(),
        "architecture_gaps": collect_architecture_gaps(gaps_file),
        "services": collect_service_status(),
    }


def build_prompt(context: dict[str, Any]) -> str:
    return (
        "You are auditing the FPAI autonomous build loop from local evidence only.\n"
        "Goal: identify systemic gaps that should become the next safe improvement specs.\n\n"
        "Look specifically for:\n"
        "- silent failures: loop ran but produced no work or no visible next action\n"
        "- recurring review failures: repeated REQUEST_CHANGES classes\n"
        "- capability gaps: PARTIAL or gap lines in architecture/build reports\n"
        "- high-correction topics: what James keeps correcting\n"
        "- unhealthy services: degraded local systemctl status\n\n"
        "Never propose money movement, treasury action, identity/KYC work, public outreach sends, "
        "secret/credential handling, production deploys, deletions, archival, or irreversible operations.\n"
        "Prefer low/med risk repo-local builds with tests and rollback.\n\n"
        "Return STRICT JSON only: an array of 1-3 objects. Each object must have:\n"
        "title (<60 chars), spec (concrete build instructions), why (one sentence), "
        "priority (1 highest), risk_class (low or med).\n\n"
        "Local system evidence JSON:\n"
        f"{json.dumps(context, ensure_ascii=False, sort_keys=True)}"
    )


def run_claude_prompt(prompt: str, timeout: int = 90) -> str:
    return call_model(prompt, task_type="audit")["response"]


def run_self_audit(
    *,
    claude_runner: Callable[[str], str] | None = None,
    context: dict[str, Any] | None = None,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    reviews_dir: Path = DEFAULT_REVIEWS_DIR,
    gaps_file: Path = DEFAULT_GAPS_FILE,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    if os.environ.get("SELF_AUDIT_DISABLE") == "1":
        return []
    audit_context = context or build_audit_context(ops_ledger=ops_ledger, reviews_dir=reviews_dir, gaps_file=gaps_file, now=now)
    runner = claude_runner or run_claude_prompt
    try:
        raw = runner(build_prompt(audit_context))
    except Exception as exc:
        log.warning("self-audit claude call failed: %s", exc)
        return []
    try:
        return validate_specs(parse_json_array(raw))
    except ValueError as exc:
        log.warning("self-audit returned invalid JSON/specs: %s", exc)
        return []


def parse_json_array(raw: str) -> list[Any]:
    text = raw.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end <= start:
            raise ValueError("no JSON array found")
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON array: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("top-level output must be an array")
    return parsed


def validate_specs(items: list[Any]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = compact(str(item.get("title", "")))
        spec = compact(str(item.get("spec", "")))
        why = compact(str(item.get("why", "")))
        risk = compact(str(item.get("risk_class", "")).lower())
        priority = item.get("priority", len(valid) + 1)
        if not title or len(title) >= TITLE_LIMIT or not spec or not why:
            continue
        if risk not in RISK_CLASSES:
            continue
        joined = f"{title} {spec} {why}"
        if FORBIDDEN_RE.search(joined):
            continue
        valid.append({"title": title, "spec": spec, "why": why, "priority": priority, "risk_class": risk})
        if len(valid) >= MAX_SPECS:
            break
    return valid


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def read_counter(path: Path) -> int:
    try:
        return max(0, int(path.read_text(encoding="utf-8").strip() or "0"))
    except (OSError, ValueError):
        return 0


def should_trigger_audit(
    *,
    queue_empty: bool,
    last_audit_text: str | None,
    merged_since_audit: int,
    now: datetime | None = None,
    idle_gap_hours: float = 2.0,
    daily_limit_hours: float = 24.0,
) -> TriggerDecision:
    current = now or utc_now()
    last = parse_audit_stamp(last_audit_text)
    age_hours = None if last is None else (current - last).total_seconds() / 3600.0
    trigger = detect_trigger_reason(
        queue_empty=queue_empty,
        age_hours=age_hours,
        merged_since_audit=merged_since_audit,
        idle_gap_hours=idle_gap_hours,
    )
    if not trigger:
        return TriggerDecision(False, None, "no trigger condition met", age_hours, merged_since_audit)
    if age_hours is not None and age_hours < daily_limit_hours:
        return TriggerDecision(False, trigger, "daily audit cap active", age_hours, merged_since_audit)
    return TriggerDecision(True, trigger, f"trigger={trigger}", age_hours, merged_since_audit)


def detect_trigger_reason(
    *,
    queue_empty: bool,
    age_hours: float | None,
    merged_since_audit: int,
    idle_gap_hours: float = 2.0,
) -> str | None:
    idle_due = queue_empty and (age_hours is None or age_hours > idle_gap_hours)
    merge_due = merged_since_audit >= 10
    if merge_due:
        return "merge_count"
    if idle_due:
        return "idle"
    return None


def trigger_from_files(
    *,
    queue_empty: bool,
    last_audit_file: Path = DEFAULT_LAST_AUDIT,
    merged_counter_file: Path = DEFAULT_MERGED_COUNTER,
    now: datetime | None = None,
) -> TriggerDecision:
    last_text = read_text(last_audit_file, limit=100)
    merged = read_counter(merged_counter_file)
    return should_trigger_audit(queue_empty=queue_empty, last_audit_text=last_text, merged_since_audit=merged, now=now)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate idle self-audit improvement specs.")
    parser.add_argument("--output", type=Path, help="write validated specs JSON to this path")
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--reviews-dir", type=Path, default=DEFAULT_REVIEWS_DIR)
    parser.add_argument("--gaps-file", type=Path, default=DEFAULT_GAPS_FILE)
    parser.add_argument("--trigger-name", action="store_true", help="print trigger name, or nothing")
    parser.add_argument("--queue-empty", choices=("0", "1"), default="0")
    parser.add_argument("--last-audit-file", type=Path, default=DEFAULT_LAST_AUDIT)
    parser.add_argument("--merged-counter-file", type=Path, default=DEFAULT_MERGED_COUNTER)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    if args.trigger_name:
        decision = trigger_from_files(
            queue_empty=args.queue_empty == "1",
            last_audit_file=args.last_audit_file,
            merged_counter_file=args.merged_counter_file,
        )
        if decision.should_run and decision.trigger:
            print(decision.trigger)
        return 0

    specs = run_self_audit(ops_ledger=args.ops_ledger, reviews_dir=args.reviews_dir, gaps_file=args.gaps_file)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(specs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(specs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
