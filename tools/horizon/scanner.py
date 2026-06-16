#!/usr/bin/env python3
"""Horizon Scanner Agent.

One scan looks at recent life, buildstream, and interaction signals. It logs
every run, but surfaces only one predictive Telegram message when a threshold
crosses.
"""
from __future__ import annotations

import argparse
import json
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
DEFAULT_CONFIG = Path(__file__).with_name("horizon_config.json")
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_DISABLE_FILE = Path(os.environ.get("HORIZON_DISABLE_FILE", "/opt/fpai-build/.horizon_disabled"))
DEFAULT_REGISTRY = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"
DEFAULT_SPECS_DIR = REPO_ROOT / "core" / "BUILD" / "specs"
DEFAULT_RESULTS_DIR = REPO_ROOT / "core" / "BUILD" / "results"

LOW_ENERGY_WORDS = re.compile(r"\b(low energy|exhausted|depleted|tired|wiped|drained|fatigue)\b", re.I)
QUESTION_WORDS = re.compile(r"\b(what|why|how|when|where|should|could|would|can|do|does|is|are)\b", re.I)
STOP_TOPICS = {
    "the", "and", "for", "with", "from", "that", "this", "what", "when", "where",
    "should", "could", "would", "james", "system", "build", "today", "tomorrow",
}


@dataclass(frozen=True)
class Signal:
    kind: str
    title: str
    detail: str
    severity: int = 1
    evidence: dict[str, Any] | None = None


@dataclass(frozen=True)
class ScanResult:
    disabled: bool
    signal: bool
    selected: Signal | None
    signals: tuple[Signal, ...]
    message: str | None
    telegram_sent: bool
    ledger_written: bool


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        raw = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "energy_low_days_threshold": int(data.get("energy_low_days_threshold", 3)),
        "build_stall_repeat_threshold": int(data.get("build_stall_repeat_threshold", 2)),
        "revert_streak_threshold": int(data.get("revert_streak_threshold", 3)),
        "topic_recurrence_threshold": int(data.get("topic_recurrence_threshold", 3)),
        "silence_hours_threshold": int(data.get("silence_hours_threshold", 24)),
        "active_hours_utc": list(data.get("active_hours_utc", [6, 20])),
    }


def dsn_from_env() -> str | None:
    for key in ("BRAIN_INDEX_DB_URL", "DATABASE_URL", "DB_URL"):
        if os.environ.get(key):
            return os.environ[key]
    return None


def read_jsonl(path: Path, *, since: datetime | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if since:
            ts = parse_time(row.get("ts") or row.get("timestamp") or row.get("created_at") or row.get("at"))
            if ts and ts < since:
                continue
        rows.append(row)
    return rows


def _table_columns(conn: Any, table: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'brain_index'
               AND table_name = %s
            """,
            (table,),
        )
        return {str(row[0]) for row in cur.fetchall()}


def _query_table(conn: Any, table: str, *, since: datetime, limit: int = 500) -> list[dict[str, Any]]:
    columns = _table_columns(conn, table)
    if not columns:
        return []
    time_col = next((c for c in ("at", "created_at", "updated_at", "initiated_at", "timestamp", "ts") if c in columns), None)
    sql = f'SELECT to_jsonb(t) FROM brain_index."{table}" AS t'
    params: tuple[Any, ...] = ()
    if time_col:
        sql += f' WHERE "{time_col}" > %s ORDER BY "{time_col}" DESC'
        params = (since,)
    sql += " LIMIT %s"
    params = params + (limit,)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(row[0] or {}) for row in cur.fetchall()]


def read_brain_index_streams(*, since: datetime) -> dict[str, list[dict[str, Any]]]:
    dsn = dsn_from_env()
    if not dsn:
        return {"life_events": [], "decisions": [], "thread": [], "tg_messages": [], "probe_sessions": []}
    try:
        import psycopg  # type: ignore
    except ImportError:
        return {"life_events": [], "decisions": [], "thread": [], "tg_messages": [], "probe_sessions": []}
    out: dict[str, list[dict[str, Any]]] = {}
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            for table in ("life_events", "decisions", "thread", "tg_messages", "probe_sessions"):
                try:
                    out[table] = _query_table(conn, table, since=since)
                except Exception:
                    out[table] = []
    except Exception:
        return {"life_events": [], "decisions": [], "thread": [], "tg_messages": [], "probe_sessions": []}
    return out


def _text(row: dict[str, Any], *keys: str) -> str:
    parts: list[str] = []
    for key in keys:
        value = row.get(key)
        if isinstance(value, (list, tuple)):
            parts.extend(str(v) for v in value if v)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).strip()


def _number(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _day_key(row: dict[str, Any]) -> str | None:
    ts = parse_time(row.get("at") or row.get("created_at") or row.get("timestamp") or row.get("ts"))
    if ts:
        return ts.date().isoformat()
    day = row.get("date") or row.get("day")
    return str(day)[:10] if day else None


def topic_key(text: str) -> str | None:
    cleaned = re.sub(r"https?://\S+", "", text.lower())
    words = [w for w in re.findall(r"[a-z][a-z0-9_-]{2,}", cleaned) if w not in STOP_TOPICS]
    if not words:
        return None
    return " ".join(words[:5])


def analyze_life_events(events: Iterable[dict[str, Any]], config: dict[str, Any]) -> list[Signal]:
    rows = list(events)
    signals: list[Signal] = []
    low_days: set[str] = set()
    topics: Counter[str] = Counter()
    unresolved = 0
    mood_points: list[tuple[datetime, float]] = []
    for row in rows:
        text = _text(row, "topic", "theme", "title", "summary", "text", "body", "context", "event")
        energy = _number(row, "energy", "energy_level", "energy_score")
        day = _day_key(row)
        if day and ((energy is not None and energy <= 3) or LOW_ENERGY_WORDS.search(text)):
            low_days.add(day)
        topic = _text(row, "topic", "theme", "category") or topic_key(text)
        if topic:
            topics[topic.lower()] += 1
        status = str(row.get("status") or row.get("state") or "").lower()
        action = _text(row, "action", "action_taken", "resolution", "resolved_at")
        friction = str(row.get("type") or row.get("kind") or row.get("category") or "").lower()
        if ("friction" in friction or status in {"open", "unresolved", "stuck", "blocked"}) and not action:
            unresolved += 1
        mood = _number(row, "mood", "mood_score", "mood_level")
        ts = parse_time(row.get("at") or row.get("created_at") or row.get("timestamp") or row.get("ts"))
        if mood is not None and ts:
            mood_points.append((ts, mood))
    threshold = int(config["energy_low_days_threshold"])
    if len(low_days) >= threshold:
        signals.append(Signal(
            "energy_low",
            f"Low energy flagged {len(low_days)} days in the last 7",
            "James-state may need load reduction before more build output arrives.",
            severity=4,
            evidence={"days": sorted(low_days)},
        ))
    for topic, count in topics.most_common(3):
        if count >= int(config["topic_recurrence_threshold"]):
            signals.append(Signal(
                "life_theme_recurrence",
                f"{topic} repeated {count} times in life data",
                "Repeated life signal is becoming an emerging priority, not background noise.",
                severity=2,
                evidence={"topic": topic, "count": count},
            ))
            break
    if unresolved >= 2:
        signals.append(Signal(
            "unresolved_friction",
            f"{unresolved} unresolved friction items are still open",
            "The system may need to remove drag before adding new commitments.",
            severity=2,
            evidence={"count": unresolved},
        ))
    mood_points.sort()
    if len(mood_points) >= 4:
        half = len(mood_points) // 2
        early = sum(v for _, v in mood_points[:half]) / half
        late = sum(v for _, v in mood_points[half:]) / (len(mood_points) - half)
        if late <= early - 1:
            signals.append(Signal(
                "mood_declining",
                "Mood slope is declining across recent life entries",
                "The response should lighten load rather than ask for more decisions.",
                severity=3,
                evidence={"early_avg": round(early, 2), "late_avg": round(late, 2)},
            ))
    return signals


def load_registry_state(
    registry_path: Path = DEFAULT_REGISTRY,
    specs_dir: Path = DEFAULT_SPECS_DIR,
    results_dir: Path = DEFAULT_RESULTS_DIR,
) -> dict[str, Any]:
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        registry = {}
    builds = list(registry.get("active_builds") or []) if isinstance(registry, dict) else []
    counts = Counter(str(b.get("status") or "unknown") for b in builds)
    done = {Path(str(b.get("spec", ""))).stem for b in builds if str(b.get("status")) in {"done", "merged"}}
    result_ids = {p.name.removesuffix(".result.md") for p in results_dir.glob("*.result.md")} if results_dir.exists() else set()
    queued_specs = []
    if specs_dir.exists():
        for spec in specs_dir.glob("*.md"):
            sid = spec.stem
            if sid not in done and sid not in result_ids:
                queued_specs.append(sid)
    return {"builds": builds, "counts": dict(counts), "queued_specs": queued_specs}


def _decision_id(row: dict[str, Any]) -> str:
    return _text(row, "id", "decision_id", "slug", "title", "topic", "question")[:120] or "unknown"


def analyze_buildstream(
    decisions: Iterable[dict[str, Any]],
    ops_rows: Iterable[dict[str, Any]],
    registry_state: dict[str, Any],
    config: dict[str, Any],
) -> list[Signal]:
    signals: list[Signal] = []
    blocked_counts: Counter[str] = Counter()
    for row in decisions:
        status = str(row.get("status") or row.get("state") or "").lower()
        blocked_n = int(_number(row, "blocked_count", "stall_count", "block_count") or 0)
        if status == "blocked" or blocked_n:
            blocked_counts[_decision_id(row)] += max(1, blocked_n)
    for row in ops_rows:
        event = str(row.get("event") or row.get("type") or row.get("status") or "").lower()
        if "blocked" in event:
            blocked_counts[_decision_id(row)] += 1
    threshold = int(config["build_stall_repeat_threshold"])
    if blocked_counts:
        decision, count = blocked_counts.most_common(1)[0]
        if count >= threshold:
            signals.append(Signal(
                "build_stall",
                f"{decision} blocked {count} times",
                "Repeated blockage usually means the spec needs a manual look before another build attempt.",
                severity=4,
                evidence={"decision": decision, "count": count},
            ))
    recent_events = [
        str(row.get("event") or row.get("type") or "").lower()
        for row in sorted(ops_rows, key=lambda r: parse_time(r.get("ts") or r.get("timestamp") or r.get("at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    ]
    streak = 0
    for event in recent_events:
        if "revert" in event or "import_failure" in event or "import failure" in event:
            streak += 1
        elif event:
            break
    if streak >= int(config["revert_streak_threshold"]):
        signals.append(Signal(
            "revert_streak",
            f"{streak} revert/import-failure events in a row",
            "Buildstream stability is the issue; new work should pause until imports stop failing.",
            severity=4,
            evidence={"streak": streak},
        ))
    counts = registry_state.get("counts") or {}
    queued = int(counts.get("queued", 0)) + int(counts.get("pending", 0)) + len(registry_state.get("queued_specs") or [])
    building = int(counts.get("building", 0))
    blocked = int(counts.get("blocked", 0))
    if blocked >= 3:
        signals.append(Signal(
            "blocked_builds_accumulating",
            f"{blocked} builds are blocked",
            "Blocked work is accumulating faster than it is being cleared.",
            severity=3,
            evidence={"blocked": blocked},
        ))
    if queued + building >= 4:
        signals.append(Signal(
            "build_load",
            f"{queued + building} builds are queued or building",
            "The system is producing output that James may need capacity to absorb.",
            severity=2,
            evidence={"queued": queued, "building": building},
        ))
    proposal_events = [
        row for row in ops_rows
        if re.search(r"(council|proposal|self_diagnostic|self_audit)", str(row.get("event") or row.get("type") or ""), re.I)
    ]
    if queued > 0 and not proposal_events:
        signals.append(Signal(
            "proposal_drought",
            "No council/proposal events appeared while build work remains queued",
            "The queue may be stale or the system may be overloaded instead of proposing the next useful move.",
            severity=2,
            evidence={"queued": queued},
        ))
    return signals


def _message_topic(row: dict[str, Any]) -> str | None:
    text = _text(row, "text", "body", "message", "content", "topic", "title")
    if not text:
        return None
    if "?" in text or QUESTION_WORDS.search(text):
        return topic_key(text)
    return None


def analyze_interactions(
    rows: Iterable[dict[str, Any]],
    config: dict[str, Any],
    *,
    now: datetime,
    source_available: bool,
) -> list[Signal]:
    messages = list(rows)
    signals: list[Signal] = []
    timestamps = [
        ts for ts in (
            parse_time(row.get("at") or row.get("created_at") or row.get("timestamp") or row.get("ts"))
            for row in messages
        )
        if ts
    ]
    if timestamps:
        latest = max(timestamps)
        silence = (now - latest).total_seconds() / 3600
        if silence >= int(config["silence_hours_threshold"]):
            signals.append(Signal(
                "silence",
                f"No interaction for {silence:.0f} hours",
                "James may be unavailable or disengaged; avoid assuming he can absorb new outputs.",
                severity=3,
                evidence={"hours": round(silence, 1)},
            ))
    elif source_available:
        signals.append(Signal(
            "silence",
            "No interaction rows in the last 7 days",
            "James may be unavailable or the interaction stream may be broken; avoid assuming he can absorb new outputs.",
            severity=3,
            evidence={"hours": ">=168"},
        ))
    topics: Counter[str] = Counter()
    for row in messages:
        topic = _message_topic(row)
        if topic:
            topics[topic] += 1
    for topic, count in topics.most_common(2):
        if count >= int(config["topic_recurrence_threshold"]):
            signals.append(Signal(
                "interaction_topic_recurrence",
                f"{topic} came up {count} times in interaction history",
                "The answer may not be retained or the underlying issue is unresolved.",
                severity=3,
                evidence={"topic": topic, "count": count},
            ))
            break
    active_start, active_end = [int(x) for x in config.get("active_hours_utc", [6, 20])[:2]]
    late = [ts for ts in timestamps if ts.hour < active_start or ts.hour >= active_end]
    if len(late) >= 3:
        signals.append(Signal(
            "late_night_sessions",
            f"{len(late)} interactions landed outside active hours",
            "Late-session patterns can mean overload; the next surface should bias toward closure.",
            severity=2,
            evidence={"count": len(late), "active_hours_utc": [active_start, active_end]},
        ))
    return signals


def analyze_probe_sessions(rows: Iterable[dict[str, Any]]) -> list[Signal]:
    sessions = list(rows)
    signals: list[Signal] = []
    if not sessions:
        return signals
    total = len(sessions)
    engaged = sum(1 for row in sessions if bool(row.get("engaged")))
    completed = sum(1 for row in sessions if bool(row.get("completed_spark")) or bool(row.get("completed_onboarding")))
    qualities = [
        float(row["quality_score"])
        for row in sessions
        if row.get("quality_score") is not None
    ]
    if total >= 5 and engaged / max(total, 1) < 0.30:
        signals.append(Signal(
            "probe_drop_rate_spike",
            f"Probe engagement is low: {engaged}/{total} engaged",
            "Outbound should pause or narrow before adding more people.",
            severity=5,
            evidence={"total": total, "engaged": engaged},
        ))
    if total >= 5 and completed / max(total, 1) < 0.30:
        signals.append(Signal(
            "probe_completion_low",
            f"Probe completion is low: {completed}/{total} completed",
            "Spark routing may be losing people before a meaningful exchange.",
            severity=4,
            evidence={"total": total, "completed": completed},
        ))
    if qualities:
        avg = sum(qualities) / len(qualities)
        if len(qualities) >= 3 and avg < 0.50:
            signals.append(Signal(
                "probe_quality_declining",
                f"Probe quality score is declining: avg {avg:.2f}",
                "Conversation routing quality should be repaired before the next scale-up.",
                severity=5,
                evidence={"avg_quality": round(avg, 3), "scored": len(qualities)},
            ))
    return signals


def cross_correlate(signals: Iterable[Signal]) -> list[Signal]:
    by_kind = {s.kind: s for s in signals}
    out: list[Signal] = []
    if "energy_low" in by_kind and "build_load" in by_kind:
        out.append(Signal(
            "energy_low_build_load",
            f"{by_kind['energy_low'].title} while {by_kind['build_load'].title.lower()}",
            "System output may outrun James's current capacity to absorb it.",
            severity=6,
            evidence={"parts": ["energy_low", "build_load"]},
        ))
    if "mood_declining" in by_kind and "blocked_builds_accumulating" in by_kind:
        out.append(Signal(
            "mood_declining_blocked_builds",
            "Mood is declining while blocked builds are accumulating",
            "The system should reduce friction before asking for another upstream decision.",
            severity=5,
            evidence={"parts": ["mood_declining", "blocked_builds_accumulating"]},
        ))
    return out


def select_signal(signals: Iterable[Signal]) -> Signal | None:
    ordered = sorted(signals, key=lambda s: (s.severity, s.kind), reverse=True)
    return ordered[0] if ordered else None


def sentence_count(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def enforce_three_sentences(text: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if len(sentences) <= 3:
        return " ".join(sentences)
    return " ".join(sentences[:3])


def fallback_message(signal: Signal) -> str:
    question = ""
    if signal.kind == "energy_low_build_load":
        question = " Worth pausing the council until capacity returns?"
    elif signal.kind == "build_stall":
        question = " Worth a manual spec look before it builds again?"
    return enforce_three_sentences(f"{signal.title}. {signal.detail}{question}")


def compose_message(signal: Signal, *, composer: Callable[[Signal], str] | None = None) -> str:
    if composer:
        return enforce_three_sentences(composer(signal))
    claude = shutil.which("claude")
    if not claude:
        return fallback_message(signal)
    prompt = (
        "Compose one Telegram message for James from this Horizon Scanner signal. "
        "Max 3 sentences. It must say: pattern detected, why it matters now, and "
        "one optional question only if useful. No digest, no list.\n\n"
        f"Signal JSON:\n{json.dumps(signal.__dict__, default=str, sort_keys=True)}"
    )
    try:
        result = subprocess.run(
            [claude, "-p", prompt, "--effort", "medium"],
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except Exception:
        return fallback_message(signal)
    if result.returncode != 0 or not result.stdout.strip():
        return fallback_message(signal)
    return enforce_three_sentences(result.stdout.strip())


def default_send_telegram(message: str, *, repo_root: Path = REPO_ROOT) -> bool:
    script = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    if not script.exists():
        return False
    try:
        result = subprocess.run([str(script), message], cwd=repo_root, check=False, timeout=20, text=True, capture_output=True)
    except Exception:
        return False
    return result.returncode == 0 and "sent" in (result.stdout or "").lower()


def log_scan(ledger: Path, *, selected: Signal | None, sent: bool) -> bool:
    row = {
        "ts": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": "horizon_scan",
        "type": "horizon_scan",
        "signal": "yes" if selected else "no",
        "detail": {
            "pattern": selected.title if selected else None,
            "kind": selected.kind if selected else None,
            "why_now": selected.detail if selected else None,
            "evidence": selected.evidence if selected else None,
            "telegram_sent": sent,
        },
        "loop": "horizon_scanner",
        "cost": "$0 marginal unless claude CLI uses flat plan",
    }
    try:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return True
    except OSError:
        return False


def recent_horizon_signal_lines(
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    *,
    now: datetime | None = None,
    hours: int = 24,
) -> list[str]:
    current = now or utc_now()
    rows = read_jsonl(ops_ledger, since=current - timedelta(hours=hours))
    lines: list[str] = []
    for row in rows:
        if str(row.get("event") or row.get("type")) != "horizon_scan":
            continue
        if str(row.get("signal") or "").lower() != "yes":
            continue
        detail = row.get("detail") if isinstance(row.get("detail"), dict) else {}
        pattern = detail.get("pattern") or row.get("pattern")
        if not pattern:
            continue
        ts = str(row.get("ts") or row.get("timestamp") or "")[:16].replace("T", " ")
        lines.append(f"{ts} · {pattern}" if ts else str(pattern))
    return lines


def run_scan(
    *,
    config_path: Path = DEFAULT_CONFIG,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    disable_file: Path = DEFAULT_DISABLE_FILE,
    now: datetime | None = None,
    streams: dict[str, list[dict[str, Any]]] | None = None,
    ops_rows: list[dict[str, Any]] | None = None,
    registry_state: dict[str, Any] | None = None,
    composer: Callable[[Signal], str] | None = None,
    sender: Callable[[str], bool] | None = None,
) -> ScanResult:
    if os.environ.get("HORIZON_DISABLE") == "1" or disable_file.exists():
        return ScanResult(True, False, None, (), None, False, False)
    current = now or utc_now()
    config = load_config(config_path)
    since = current - timedelta(days=7)
    stream_data = streams if streams is not None else read_brain_index_streams(since=since)
    interaction_source_available = streams is not None or bool(dsn_from_env())
    rows_for_ops = ops_rows if ops_rows is not None else read_jsonl(ops_ledger, since=since)
    reg = registry_state if registry_state is not None else load_registry_state()
    all_interactions = list(stream_data.get("thread") or []) + list(stream_data.get("tg_messages") or [])
    base_signals = (
        analyze_life_events(stream_data.get("life_events") or [], config)
        + analyze_buildstream(stream_data.get("decisions") or [], rows_for_ops, reg, config)
        + analyze_interactions(all_interactions, config, now=current, source_available=interaction_source_available)
        + analyze_probe_sessions(stream_data.get("probe_sessions") or [])
    )
    all_signals = tuple(cross_correlate(base_signals) + base_signals)
    selected = select_signal(all_signals)
    message = compose_message(selected, composer=composer) if selected else None
    sent = False
    if selected and message:
        send = sender or default_send_telegram
        sent = bool(send(message))
    ledger_written = log_scan(ops_ledger, selected=selected, sent=sent)
    return ScanResult(False, bool(selected), selected, all_signals, message, sent, ledger_written)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FPAI Horizon Scanner once.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--disable-file", type=Path, default=DEFAULT_DISABLE_FILE)
    parser.add_argument("--no-send", action="store_true", help="compose/log but do not send Telegram")
    parser.add_argument("--no-claude", action="store_true", help="use deterministic fallback composition")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    sender = (lambda _message: False) if args.no_send else None
    composer = fallback_message if args.no_claude else None
    result = run_scan(
        config_path=args.config,
        ops_ledger=args.ops_ledger,
        disable_file=args.disable_file,
        sender=sender,
        composer=composer,
    )
    if args.json:
        print(json.dumps({
            "disabled": result.disabled,
            "signal": result.signal,
            "selected": result.selected.__dict__ if result.selected else None,
            "message": result.message,
            "telegram_sent": result.telegram_sent,
            "ledger_written": result.ledger_written,
        }, sort_keys=True, default=str))
    elif result.message:
        print(result.message)
    else:
        print("horizon: silent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
