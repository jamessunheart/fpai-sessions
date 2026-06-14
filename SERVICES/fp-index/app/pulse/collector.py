"""Collect real outward-outcome metrics from the live system.

Reads from existing databases and logs. No LLM calls. No assumptions —
if a source is missing, that metric is recorded as null with a reason.

Each run produces a single snapshot that gets appended to pulse_snapshots.jsonl.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from ..field_sensor.registry import BRAIN_DIR, ensure_brain_dir

logger = logging.getLogger(__name__)

PULSE_VERSION = "v1.0.0-2026-04-24"
PULSE_SNAPSHOTS = BRAIN_DIR / "pulse_snapshots.jsonl"

ZEN_PASS_DB = Path("/opt/fpai/apps/zen-village/data/zen_pass.db")
BOOKINGS_DB = Path("/opt/fpai/apps/zen-village/data/bookings.db")
FP_INDEX_DB = Path("/opt/fpai/services/fp-index/fp_index.db")
NGINX_ACCESS_LOG = Path("/var/log/nginx/access.log")

TRACKED_DOMAINS = [
    "fullpotential.ai", "fullpotential.com", "zenvillagecr.com",
    "mydreamspace.com", "coravida.com",
]


def _safe_sqlite_count(db_path: Path, query: str, params: tuple = ()) -> Optional[int]:
    if not db_path.exists():
        return None
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(query, params).fetchone()
            return int(row[0]) if row and row[0] is not None else 0
    except sqlite3.Error as e:
        logger.debug(f"[PULSE] sqlite error on {db_path.name}: {e}")
        return None


def _safe_sqlite_sum(db_path: Path, query: str, params: tuple = ()) -> Optional[float]:
    if not db_path.exists():
        return None
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(query, params).fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0
    except sqlite3.Error as e:
        logger.debug(f"[PULSE] sqlite error on {db_path.name}: {e}")
        return None


def _collect_zen_village() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    return {
        "passes_total": _safe_sqlite_count(ZEN_PASS_DB, "SELECT COUNT(*) FROM passes"),
        "passes_last_7d": _safe_sqlite_count(
            ZEN_PASS_DB, "SELECT COUNT(*) FROM passes WHERE created_at >= ?", (week_ago,),
        ),
        "passes_paid_total": _safe_sqlite_count(
            ZEN_PASS_DB, "SELECT COUNT(*) FROM passes WHERE payment_status='paid'",
        ),
        "passes_checked_in": _safe_sqlite_count(
            ZEN_PASS_DB, "SELECT COUNT(*) FROM passes WHERE checked_in=1",
        ),
        "events_active": _safe_sqlite_count(
            ZEN_PASS_DB, "SELECT COUNT(*) FROM events WHERE active=1",
        ),
        "zen_pass_revenue_total": _safe_sqlite_sum(
            ZEN_PASS_DB, "SELECT COALESCE(SUM(amount_paid), 0) FROM passes WHERE payment_status='paid'",
        ),
        "zen_pass_revenue_last_7d": _safe_sqlite_sum(
            ZEN_PASS_DB,
            "SELECT COALESCE(SUM(amount_paid), 0) FROM passes WHERE payment_status='paid' AND created_at >= ?",
            (week_ago,),
        ),
        "transactions_total": _safe_sqlite_count(ZEN_PASS_DB, "SELECT COUNT(*) FROM transactions"),
        "bookings_total": _safe_sqlite_count(BOOKINGS_DB, "SELECT COUNT(*) FROM bookings"),
        "bookings_confirmed": _safe_sqlite_count(
            BOOKINGS_DB, "SELECT COUNT(*) FROM bookings WHERE status='confirmed'",
        ),
        "bookings_last_30d": _safe_sqlite_count(
            BOOKINGS_DB, "SELECT COUNT(*) FROM bookings WHERE check_in >= ?", (month_ago,),
        ),
        "bookings_revenue_total": _safe_sqlite_sum(
            BOOKINGS_DB, "SELECT COALESCE(SUM(total_amount), 0) FROM bookings WHERE status IN ('confirmed', 'completed')",
        ),
    }


def _collect_reach() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()

    reach: dict[str, Any] = {
        "email_subscribers_total": _safe_sqlite_count(
            FP_INDEX_DB, "SELECT COUNT(*) FROM email_subscribers WHERE active=1",
        ),
        "email_subscribers_last_7d": _safe_sqlite_count(
            FP_INDEX_DB,
            "SELECT COUNT(*) FROM email_subscribers WHERE active=1 AND created_at >= ?",
            (week_ago,),
        ),
    }

    reach["domain_hits_last_7d"] = _parse_nginx_hits(days=7)
    reach["unique_visitors_last_7d_approx"] = _parse_nginx_unique_ips(days=7)
    return reach


def _parse_nginx_hits(days: int = 7) -> Optional[dict[str, int]]:
    if not NGINX_ACCESS_LOG.exists():
        return None
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cmd = ["tail", "-n", "200000", str(NGINX_ACCESS_LOG)]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        lines = out.stdout.splitlines()
    except Exception as e:
        logger.debug(f"[PULSE] nginx tail failed: {e}")
        return None

    host_counts: dict[str, int] = {d: 0 for d in TRACKED_DOMAINS}
    host_counts["other"] = 0

    for line in lines:
        ts_match = re.search(r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})", line)
        if ts_match:
            try:
                ts = datetime.strptime(ts_match.group(1), "%d/%b/%Y:%H:%M:%S").replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue
            except ValueError:
                pass

        matched = False
        for domain in TRACKED_DOMAINS:
            if domain in line:
                host_counts[domain] += 1
                matched = True
                break
        if not matched:
            host_counts["other"] += 1

    return host_counts


def _parse_nginx_unique_ips(days: int = 7) -> Optional[dict[str, int]]:
    if not NGINX_ACCESS_LOG.exists():
        return None
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cmd = ["tail", "-n", "200000", str(NGINX_ACCESS_LOG)]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        lines = out.stdout.splitlines()
    except Exception:
        return None

    by_domain: dict[str, set[str]] = {d: set() for d in TRACKED_DOMAINS}
    by_domain["other"] = set()

    for line in lines:
        ts_match = re.search(r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})", line)
        if ts_match:
            try:
                ts = datetime.strptime(ts_match.group(1), "%d/%b/%Y:%H:%M:%S").replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue
            except ValueError:
                pass
        ip_match = re.match(r"(\d+\.\d+\.\d+\.\d+)", line)
        if not ip_match:
            continue
        ip = ip_match.group(1)
        placed = False
        for domain in TRACKED_DOMAINS:
            if domain in line:
                by_domain[domain].add(ip)
                placed = True
                break
        if not placed:
            by_domain["other"].add(ip)

    return {d: len(ips) for d, ips in by_domain.items()}


def _collect_system() -> dict[str, Any]:
    """System output metrics — how much is the organism actually producing?"""
    gap_registry = BRAIN_DIR / "gap_registry.jsonl"
    proposals_status = BRAIN_DIR / "proposals_status.json"
    probe_results = BRAIN_DIR / "probe_results.jsonl"
    events_db = BRAIN_DIR / "field_events.db"

    gaps_total = _count_jsonl(gap_registry)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    gaps_last_7d = _count_jsonl_since(gap_registry, week_ago)

    proposals_summary = {"pending": 0, "approved": 0, "rejected": 0, "shipped": 0, "total": 0}
    if proposals_status.exists():
        try:
            status = json.loads(proposals_status.read_text())
            for p in status.values():
                s = p.get("status", "unknown")
                proposals_summary[s] = proposals_summary.get(s, 0) + 1
                proposals_summary["total"] += 1
        except json.JSONDecodeError:
            pass

    latest_probe_pass_rate = None
    latest_probe_avg_score = None
    if probe_results.exists():
        try:
            from ..capability_probes.results import latest_run_summary
            s = latest_run_summary()
            if s:
                latest_probe_pass_rate = s.get("pass_rate")
                latest_probe_avg_score = s.get("avg_score")
        except Exception:
            pass

    events_sensed_total = 0
    events_gated_passed_total = 0
    if events_db.exists():
        try:
            with sqlite3.connect(events_db) as conn:
                row = conn.execute(
                    "SELECT COUNT(*), SUM(gated_passed) FROM events"
                ).fetchone()
                events_sensed_total = row[0] or 0
                events_gated_passed_total = row[1] or 0
        except sqlite3.Error:
            pass

    return {
        "field_events_sensed_total": events_sensed_total,
        "field_events_gated_passed_total": events_gated_passed_total,
        "gaps_logged_total": gaps_total,
        "gaps_logged_last_7d": gaps_last_7d,
        "proposals": proposals_summary,
        "probe_pass_rate_latest": latest_probe_pass_rate,
        "probe_avg_score_latest": latest_probe_avg_score,
    }


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text().split("\n"):
        if line.strip():
            count += 1
    return count


def _count_jsonl_since(path: Path, since: datetime) -> int:
    if not path.exists():
        return 0
    since_iso = since.isoformat()
    count = 0
    for line in path.read_text().split("\n"):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if r.get("ts", "") >= since_iso:
                count += 1
        except json.JSONDecodeError:
            continue
    return count


def collect_pulse() -> dict[str, Any]:
    """Gather one full pulse snapshot across all three sections."""
    ensure_brain_dir()
    ts = datetime.now(timezone.utc).isoformat()
    pulse = {
        "ts": ts,
        "version": PULSE_VERSION,
        "zen_village": _collect_zen_village(),
        "reach": _collect_reach(),
        "system": _collect_system(),
    }
    return pulse


def save_snapshot(pulse: dict[str, Any]) -> None:
    ensure_brain_dir()
    with PULSE_SNAPSHOTS.open("a") as f:
        f.write(json.dumps(pulse, default=str) + "\n")
    logger.info(f"[PULSE] snapshot saved at {pulse['ts']}")


def run_weekly_pulse() -> dict[str, Any]:
    """Used by the weekly scheduler. Collect + save + return snapshot."""
    pulse = collect_pulse()
    save_snapshot(pulse)
    return pulse
