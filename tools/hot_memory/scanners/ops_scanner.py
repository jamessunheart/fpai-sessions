#!/usr/bin/env python3
"""Scan ops ledger and local host health into hot-memory facts."""
from __future__ import annotations

import argparse
import os
import socket
from pathlib import Path
from shutil import disk_usage

from tools.hot_memory.common import DEFAULT_HOT_DIR, DEFAULT_OPS_LEDGER, REPO_ROOT, compact_facts, fact, file_date, read_jsonl_tail, write_scan
from tools.build_loop import activation_audit


def collect(repo_root: Path = REPO_ROOT, ops_ledger: Path = DEFAULT_OPS_LEDGER):
    facts = []
    facts.extend(_resource_inventory_facts(repo_root))
    host = os.environ.get("FPAI_SERVER_ID") or socket.gethostname()
    facts.append(fact(f"Bot/build host visible as {host}; repo readable={repo_root.exists()}", "local host", file_date(repo_root), weight=6, category="ops"))
    try:
        load1, load5, _ = os.getloadavg()
        facts.append(fact(f"Host load is 1m={load1:.2f}, 5m={load5:.2f}", "os.getloadavg", file_date(repo_root), weight=5, category="ops"))
    except OSError:
        pass
    try:
        usage = disk_usage(repo_root)
        free_pct = usage.free / usage.total * 100 if usage.total else 0.0
        facts.append(fact(f"Repo disk free is {free_pct:.1f}%", "disk_usage", file_date(repo_root), weight=5, category="ops"))
    except OSError:
        pass
    rows = read_jsonl_tail(ops_ledger, limit=80)
    if rows:
        failures = [row for row in rows if str(row.get("event") or "").lower() in {"failed", "error"}]
        facts.append(fact(f"Ops ledger tail has {len(failures)} failures in last {len(rows)} rows", str(ops_ledger), file_date(ops_ledger), weight=7, category="ops"))
        last = rows[-1]
        detail = " ".join(str(part) for part in (last.get("event"), last.get("loop"), last.get("detail"), last.get("reason")) if part)
        if detail:
            facts.append(fact(f"Latest ops ledger event: {detail}", str(ops_ledger), file_date(ops_ledger), weight=6, category="ops"))
        # Surface latest awareness reliability score — key metric, was invisible in HOT_STATE
        probe_rows = [r for r in reversed(rows) if r.get("event") == "awareness_reliability_probe"]
        if probe_rows:
            p = probe_rows[0]
            pct = round(p.get("reliability", 0) * 100, 1)
            successes = p.get("successes", "?")
            total = p.get("total", "?")
            ts = (p.get("ts") or "")[:16]
            facts.append(fact(
                f"Awareness reliability score: {pct}% ({successes}/{total} probes passing) as of {ts}",
                str(ops_ledger), file_date(ops_ledger), weight=9, category="ops",
            ))
    activation = _activation_audit_fact(repo_root, ops_ledger)
    if activation:
        facts.append(activation)
    return compact_facts(facts, limit=12)


def _activation_audit_fact(repo_root: Path, ops_ledger: Path):
    try:
        payload = activation_audit.audit(repo_root, ops_ledger=ops_ledger)
    except Exception:
        return None
    unexplained = payload.get("unexplained_inert") or []
    counts = payload.get("counts") or {}
    if unexplained:
        preview = ", ".join(str(item) for item in unexplained[:4])
        return fact(
            f"Activation audit: {len(unexplained)} unexplained INERT merged builds ({preview})",
            "tools/build_loop/activation_audit.py",
            file_date(repo_root / "tools" / "build_loop" / "activation_audit.py"),
            weight=9,
            category="ops",
        )
    if payload.get("total"):
        return fact(
            f"Activation audit: 0 unexplained INERT merged builds; counts={dict(counts)}",
            "tools/build_loop/activation_audit.py",
            file_date(repo_root / "tools" / "build_loop" / "activation_audit.py"),
            weight=6,
            category="ops",
        )
    return None


def _resource_inventory_facts(repo_root: Path):
    path = repo_root / "core" / "STATE" / "RESOURCE_INVENTORY.md"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if "system email" in lower or "sunheartbrain_bot" in lower or "build loop" in lower:
            rows.append(fact(stripped.replace("|", " "), "core/STATE/RESOURCE_INVENTORY.md", file_date(path), weight=8, category="general"))
        if len(rows) >= 4:
            break
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--hot-dir", type=Path, default=DEFAULT_HOT_DIR)
    args = parser.parse_args(argv)
    payload = write_scan("ops", collect(args.repo_root, args.ops_ledger), hot_dir=args.hot_dir)
    print(payload["changed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
