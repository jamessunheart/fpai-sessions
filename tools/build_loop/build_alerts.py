#!/usr/bin/env python3
"""Build lifecycle alert state, ETA, digest, and queue snapshot helpers."""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import importlib.util as _ilu
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any

try:
    from tools.build_loop import build_state
except Exception:
    _state_path = Path(__file__).with_name("build_state.py")
    _spec = _ilu.spec_from_file_location("fpai_build_state_for_alerts", _state_path)
    build_state = _ilu.module_from_spec(_spec) if _spec and _spec.loader else None
    if build_state is None or _spec is None or _spec.loader is None:
        raise
    sys.modules[_spec.name] = build_state
    _spec.loader.exec_module(build_state)

CR_TZ = dt.timezone(dt.timedelta(hours=-6), name="CR")
QUIET_START = 22
QUIET_END = 7


@dataclasses.dataclass(frozen=True)
class AlertPaths:
    stats: Path
    state: Path
    digest: Path


def default_paths(config_home: Path | None = None) -> AlertPaths:
    root = config_home or Path(os.environ.get("FPAI_CONFIG_HOME", "~/.config/fpai")).expanduser()
    return AlertPaths(
        stats=Path(os.environ.get("BUILD_STATS_PATH", root / "build_stats.json")).expanduser(),
        state=Path(os.environ.get("BUILD_ALERT_STATE_PATH", root / "build_alert_state.json")).expanduser(),
        digest=Path(os.environ.get("BUILD_ALERT_DIGEST_PATH", root / "build_alert_digest.json")).expanduser(),
    )


def _now() -> dt.datetime:
    override = os.environ.get("BUILD_ALERTS_NOW")
    if override:
        text = override.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def _minutes(seconds: float | int) -> int:
    return max(1, int(round(float(seconds) / 60.0)))


def _clean(text: str, *, limit: int = 96) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _decision_label(decision_id: str) -> str:
    return decision_id if decision_id.startswith("d") else decision_id


def _stats_entries(stats: dict[str, Any]) -> list[dict[str, Any]]:
    entries = stats.get("entries")
    return entries if isinstance(entries, list) else []


def eta_text(stats: dict[str, Any]) -> str:
    durations = [
        float(row["duration_seconds"])
        for row in _stats_entries(stats)[-20:]
        if isinstance(row, dict) and isinstance(row.get("duration_seconds"), (int, float))
    ]
    if not durations:
        return "ETA unknown yet"
    median = statistics.median(durations)
    if len(durations) >= 5:
        ranked = sorted(durations)
        p90 = ranked[min(len(ranked) - 1, int(round((len(ranked) - 1) * 0.9)))]
        if p90 >= median * 1.75 and _minutes(p90) > _minutes(median):
            return f"ETA ~{_minutes(median)}m, p90 {_minutes(p90)}m"
    return f"ETA ~{_minutes(median)}m"


def _quiet_hours(now: dt.datetime) -> bool:
    hour = now.astimezone(CR_TZ).hour
    return hour >= QUIET_START or hour < QUIET_END


def _digest_item(message: str, event: str, spec_id: str, now: dt.datetime) -> dict[str, str]:
    return {"ts": _iso(now), "event": event, "spec_id": spec_id, "message": message}


def _should_batch(event: str, digest: dict[str, Any], now: dt.datetime) -> bool:
    if event == "failed":
        return False
    if _quiet_hours(now):
        return True
    if spec_id := digest.get("_current_spec_id"):
        if spec_id in set(digest.get("batched_specs", [])):
            return True
    recent_starts = [
        item
        for item in digest.get("sent_starts", [])
        if (ts := _parse_iso(item.get("ts"))) and (now - ts).total_seconds() <= 30 * 60
    ]
    digest["sent_starts"] = recent_starts
    return event == "start" and len(recent_starts) >= 3


def _record_sent(digest: dict[str, Any], event: str, spec_id: str, now: dt.datetime) -> None:
    recent = [
        item
        for item in digest.get("sent_events", [])
        if (ts := _parse_iso(item.get("ts"))) and (now - ts).total_seconds() <= 30 * 60
    ]
    recent.append({"ts": _iso(now), "event": event, "spec_id": spec_id})
    digest["sent_events"] = recent[-20:]
    if event == "start":
        starts = [
            item
            for item in digest.get("sent_starts", [])
            if (ts := _parse_iso(item.get("ts"))) and (now - ts).total_seconds() <= 30 * 60
        ]
        starts.append({"ts": _iso(now), "spec_id": spec_id})
        digest["sent_starts"] = starts[-20:]


def _format_event(
    event: str,
    decision_id: str,
    spec_id: str,
    title: str,
    stats: dict[str, Any],
    state: dict[str, Any],
    now: dt.datetime,
    reason: str = "",
) -> str:
    label = _decision_label(decision_id)
    builds = state.setdefault("builds", {})
    entry = builds.setdefault(spec_id, {})
    title_clean = _clean(title or spec_id, limit=80)
    if event == "start":
        entry.update({"decision_id": decision_id, "title": title_clean, "stage": "building", "started_at": _iso(now)})
        return f"▶️ BUILD START {label} {title_clean} · {eta_text(stats)}"
    if event == "review":
        entry["stage"] = "review"
        return f"🔍 REVIEW {label}"
    if event in {"merged", "failed"}:
        started = _parse_iso(entry.get("started_at"))
        duration = (now - started).total_seconds() if started else None
        took = f"took {_minutes(duration)}m" if duration is not None else "took unknown"
        outcome = "merged" if event == "merged" else "failed"
        entry["stage"] = outcome
        entry[f"{outcome}_at"] = _iso(now)
        if duration is not None:
            stats.setdefault("entries", []).append(
                {
                    "spec_id": spec_id,
                    "decision_id": decision_id,
                    "title": title_clean,
                    "outcome": outcome,
                    "started_at": entry.get("started_at"),
                    "completed_at": _iso(now),
                    "duration_seconds": int(duration),
                }
            )
            stats["entries"] = stats["entries"][-200:]
        if event == "merged":
            what = _clean(title or entry.get("title") or spec_id, limit=90)
            return f"✅ MERGED {label} · {took} · {what}"
        detail = _clean(reason or "build did not merge", limit=90)
        return f"❌ FAILED {label} · {detail}"
    if event == "verified":
        entry["stage"] = "verified"
        entry["verified_at"] = _iso(now)
        return f"🟢 VERIFIED-LIVE {label}"
    raise ValueError(f"unknown event: {event}")


def event_message(
    event: str,
    decision_id: str,
    spec_id: str,
    title: str,
    reason: str = "",
    *,
    paths: AlertPaths | None = None,
    now: dt.datetime | None = None,
) -> str:
    if os.environ.get("BUILD_ALERTS", "1").strip() == "0":
        return ""
    paths = paths or default_paths()
    now = now or _now()
    stats = _load_json(paths.stats, {"entries": []})
    state = _load_json(paths.state, {"builds": {}})
    digest = _load_json(paths.digest, {"pending": [], "sent_events": []})
    message = _format_event(event, decision_id, spec_id, title, stats, state, now, reason)
    digest["_current_spec_id"] = spec_id
    if _should_batch(event, digest, now):
        if event == "start":
            batched = list(digest.get("batched_specs", []))
            if spec_id not in batched:
                batched.append(spec_id)
            digest["batched_specs"] = batched[-20:]
        digest.setdefault("pending", []).append(_digest_item(message, event, spec_id, now))
        digest.pop("_current_spec_id", None)
        _write_json(paths.stats, stats)
        _write_json(paths.state, state)
        _write_json(paths.digest, digest)
        return ""
    digest.pop("_current_spec_id", None)
    _record_sent(digest, event, spec_id, now)
    _write_json(paths.stats, stats)
    _write_json(paths.state, state)
    _write_json(paths.digest, digest)
    return message


def flush_digest(*, paths: AlertPaths | None = None, now: dt.datetime | None = None, force: bool = False) -> str:
    paths = paths or default_paths()
    now = now or _now()
    digest = _load_json(paths.digest, {"pending": [], "sent_events": []})
    pending = digest.get("pending") or []
    if not pending:
        return ""
    if _quiet_hours(now) and not force:
        return ""
    counts: dict[str, int] = {}
    for item in pending:
        counts[item.get("event", "event")] = counts.get(item.get("event", "event"), 0) + 1
    sample = pending[-5:]
    lines = ["Build alerts batched while the loop was busy:"]
    lines.append(" · ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    lines.extend(f"- {item.get('message', '')}" for item in sample)
    digest["pending"] = []
    digest["batched_specs"] = []
    _record_sent(digest, "digest", "build-alerts", now)
    _write_json(paths.digest, digest)
    return "\n".join(lines)


def heartbeat(*, paths: AlertPaths | None = None, now: dt.datetime | None = None) -> None:
    if os.environ.get("BUILD_ALERTS", "1").strip() == "0":
        return
    paths = paths or default_paths()
    now = now or _now()
    state = _load_json(paths.state, {"builds": {}})
    state["last_heartbeat_at"] = _iso(now)
    _write_json(paths.state, state)


def render_queue_snapshot(repo_root: Path, *, paths: AlertPaths | None = None, now: dt.datetime | None = None) -> str:
    paths = paths or default_paths()
    now = now or _now()
    state = build_state.collect_repo_build_state(
        specs_dir=repo_root / "core" / "BUILD" / "specs",
        results_dir=repo_root / "core" / "BUILD" / "results",
        registry_path=repo_root / "core" / "BUILD" / "REGISTRY.json",
    )
    alert_state = _load_json(paths.state, {"builds": {}})
    stats = _load_json(paths.stats, {"entries": []})
    today = now.astimezone(CR_TZ).date()
    completed_today = 0
    for item in _stats_entries(stats):
        completed = _parse_iso(item.get("completed_at") if isinstance(item, dict) else None)
        if completed and completed.astimezone(CR_TZ).date() == today:
            completed_today += 1
    inflight = []
    for spec_id, item in sorted((alert_state.get("builds") or {}).items()):
        if not isinstance(item, dict):
            continue
        stage = item.get("stage")
        if stage in {"building", "review"}:
            inflight.append(f"{item.get('decision_id') or spec_id}: {stage}")
    pending = [spec.split("_", 2)[1] if spec.startswith("SPEC_d") and "_" in spec[5:] else spec for spec in state.queued_specs[:12]]
    lines = [
        "<b>Builds</b>",
        f"pending: <b>{state.queued_count}</b>" + (f" · {', '.join(pending)}" if pending else ""),
        "in flight: " + ("; ".join(inflight) if inflight else "none"),
        f"completed today: <b>{completed_today}</b>",
        f"{eta_text(stats)}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("event")
    ev.add_argument("--event", required=True, choices=["start", "review", "merged", "failed", "verified"])
    ev.add_argument("--decision-id", required=True)
    ev.add_argument("--spec-id", required=True)
    ev.add_argument("--title", default="")
    ev.add_argument("--reason", default="")
    fl = sub.add_parser("flush")
    fl.add_argument("--force", action="store_true")
    sub.add_parser("heartbeat")
    snap = sub.add_parser("snapshot")
    snap.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.cmd == "event":
        print(event_message(args.event, args.decision_id, args.spec_id, args.title, args.reason))
    elif args.cmd == "flush":
        print(flush_digest(force=args.force))
    elif args.cmd == "heartbeat":
        heartbeat()
    elif args.cmd == "snapshot":
        print(render_queue_snapshot(args.repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
