"""Read-only live status snapshot for Ember owner-chat context.

This module intentionally observes only local repo/host mirrors. It does not
route builds, merge branches, restart services, deploy, or touch secrets.
"""
from __future__ import annotations

import json
import os
import socket
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from shutil import disk_usage
from typing import Any


DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))


@dataclass(frozen=True)
class StatusSnapshot:
    queue: list[str]
    last_merge: list[str]
    health: list[str]

    def lines(self) -> list[str]:
        return [*self.queue, *self.last_merge, *self.health]


def collect_status(
    repo_root: Path | str,
    *,
    ops_ledger: Path | str = DEFAULT_OPS_LEDGER,
    max_items: int = 6,
) -> StatusSnapshot:
    root = Path(repo_root)
    return StatusSnapshot(
        queue=_queue_state(root),
        last_merge=_last_merge_state(root),
        health=_server_health(root, ops_ledger=Path(ops_ledger), max_items=max_items),
    )


def render_status_lines(snapshot: StatusSnapshot, *, max_items: int = 6) -> list[str]:
    lines = snapshot.lines()
    return lines[:max_items]


def _queue_state(repo_root: Path) -> list[str]:
    specs_dir = repo_root / "core" / "BUILD" / "specs"
    results_dir = repo_root / "core" / "BUILD" / "results"
    registry = _read_registry(repo_root)

    pending_specs: list[str] = []
    if specs_dir.exists():
        for spec in sorted(specs_dir.glob("*.md")):
            if not (results_dir / f"{spec.stem}.result.md").exists():
                pending_specs.append(spec.stem)

    statuses = Counter()
    active: list[str] = []
    for row in _registry_rows(registry):
        status = str(row.get("status") or "unknown")
        statuses[status] += 1
        if status in {"building", "queued", "ready", "merge_requested"}:
            ident = str(row.get("slug") or row.get("id") or "unknown")
            active.append(f"{ident}:{status}")

    status_bits = ", ".join(f"{key}={statuses[key]}" for key in sorted(statuses)) or "registry=empty"
    pending_preview = ", ".join(pending_specs[:3]) if pending_specs else "none"
    active_preview = ", ".join(active[:3]) if active else "none"
    return [
        f"Build queue: pending_specs={len(pending_specs)} ({pending_preview}) · {status_bits}",
        f"Active build requests: {active_preview}",
    ]


def _last_merge_state(repo_root: Path) -> list[str]:
    # Read from git log — authoritative, always current
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "log", "--oneline", "-3", "--merges"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            return [f"Last merge: {line.strip()}" for line in lines[:2]]
    except Exception:
        pass

    review = _newest_file(repo_root / "core" / "BUILD" / "reviews", "*.md")
    result_file = _newest_file(repo_root / "core" / "BUILD" / "results", "*.md")
    if review:
        verdict = _extract_review_verdict(review)
        return [f"Last merge outcome: review={verdict} · {review.name}"]
    if result_file:
        return [f"Last merge outcome: build result awaiting review · {result_file.name}"]
    return ["Last merge outcome: none found in repo mirrors"]


def _server_health(repo_root: Path, *, ops_ledger: Path, max_items: int) -> list[str]:
    host = os.environ.get("FPAI_SERVER_ID") or socket.gethostname()
    health: list[str] = []
    health.append(f"Server health: host={host} · repo_readable={repo_root.exists()}")

    try:
        load1, load5, _ = os.getloadavg()
        health.append(f"Load: 1m={load1:.2f} · 5m={load5:.2f}")
    except (AttributeError, OSError):
        health.append("Load: unavailable")

    try:
        usage = disk_usage(repo_root)
        free_pct = (usage.free / usage.total) * 100 if usage.total else 0.0
        health.append(f"Disk: free={free_pct:.1f}%")
    except OSError:
        health.append("Disk: unavailable")

    ops = _ops_summary(ops_ledger, max_items=max_items)
    if ops:
        health.append(ops)
    liveness = _liveness_summary(ops_ledger)
    if liveness:
        health.append(liveness)
    return health


def _ops_summary(path: Path, *, max_items: int) -> str:
    rows = _read_jsonl_tail(path, limit=max(25, max_items * 4))
    if not rows:
        return "Ops ledger: unavailable or empty"
    failures = [
        row
        for row in rows
        if str(row.get("event") or "").lower() in {"failed", "error"}
    ]
    last = rows[-1]
    last_bits = " ".join(
        str(part)
        for part in (last.get("loop"), last.get("event"), last.get("detail"))
        if part
    )
    if failures:
        fail = failures[-1]
        return f"Ops ledger: recent_failures={len(failures)} · last_failure={fail.get('loop')} {fail.get('detail')}"
    return f"Ops ledger: recent_failures=0 · last={last_bits[:160]}"


def _liveness_summary(path: Path) -> str:
    rows = _read_jsonl_tail(path, limit=500)
    latest: dict[str, str] = {}
    for row in rows:
        event = str(row.get("event") or "")
        if not event.startswith("liveness:"):
            continue
        ident = str(row.get("spec_id") or "").strip()
        if not ident:
            detail = str(row.get("detail") or "")
            ident = detail.split()[0] if detail.startswith("SPEC_") else ""
        if not ident:
            continue
        status = str(row.get("liveness_status") or "").strip()
        if not status:
            status = {
                "liveness:pass": "live",
                "liveness:partial": "partial",
                "liveness:planned": "planned",
                "liveness:fail": "dead",
            }.get(event, "partial")
        latest[ident] = status
    if not latest:
        return ""
    counts = Counter(latest.values())
    not_live = [ident for ident, status in latest.items() if status in {"partial", "dead"}]
    suffix = f" · not_live={', '.join(not_live[:3])}" if not_live else ""
    return (
        "Liveness: "
        f"running={counts.get('live', 0)} · partial={counts.get('partial', 0)} · "
        f"dead={counts.get('dead', 0)} · planned={counts.get('planned', 0)}"
        f"{suffix}"
    )


def _read_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "core" / "BUILD" / "REGISTRY.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _registry_rows(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = registry.get("active_builds")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _newest_file(directory: Path, pattern: str) -> Path | None:
    try:
        files = [path for path in directory.glob(pattern) if path.is_file()]
    except OSError:
        return None
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def _extract_review_verdict(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "unknown"
    for line in text.splitlines()[:20]:
        if "Verdict" in line:
            return " ".join(line.replace("*", "").split())[:120]
        if "PASS" in line or "APPROVE" in line or "REQUEST_CHANGES" in line:
            return " ".join(line.replace("*", "").split())[:120]
    return "unknown"


def _read_jsonl_tail(path: Path, *, limit: int) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows
