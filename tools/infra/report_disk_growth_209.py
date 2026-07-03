#!/usr/bin/env python3
"""Read-only disk growth report for host 209.74.93.72."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


SPEC_ID = "SPEC_d147_self-audit-infra-209-disk-impro"
DECISION_ID = "d147"
TARGET_IP = "209.74.93.72"
REPORT_LOOP = "infra-209-disk-growth-report"
DEFAULT_ROOTS = (
    "/home",
    "/backup",
    "/var",
    "/usr/local/cpanel",
    "/opt",
)


class DiskReportError(RuntimeError):
    pass


Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DiskReportError(f"missing evidence file: {path}") from exc


def fleet_evidence(repo_root: Path) -> list[str]:
    snapshot = repo_root / "core" / "STATE" / "FLEET_SNAPSHOT.md"
    text = _read_text(snapshot)
    evidence = [
        line.strip()
        for line in text.splitlines()
        if "209.74.93.72" in line
        or ("209 disk" in line.lower())
        or ("disk" in line.lower() and "67%" in line and "70%" in line)
    ]
    if not any("209" in line and "disk" in line.lower() for line in evidence):
        raise DiskReportError("209 disk trend evidence not found in FLEET_SNAPSHOT.md")
    return evidence


def local_ips() -> set[str]:
    override = os.environ.get("FPAI_D147_HOST_IPS")
    if override is not None:
        return {part.strip() for part in override.replace(",", " ").split() if part.strip()}
    try:
        proc = subprocess.run(
            ["hostname", "-I"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return set()
    return {part.strip() for part in proc.stdout.split() if part.strip()}


def on_target_host(ips: Iterable[str]) -> bool:
    return TARGET_IP in set(ips)


def default_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=float(os.environ.get("FPAI_D147_CMD_TIMEOUT", "300")),
    )


def parse_df(output: str) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            rows.append(
                {
                    "filesystem": parts[0],
                    "size_bytes": int(parts[1]),
                    "used_bytes": int(parts[2]),
                    "available_bytes": int(parts[3]),
                    "use_percent": int(parts[4].rstrip("%")),
                    "mounted_on": parts[5],
                }
            )
        except ValueError:
            continue
    return rows


def parse_du(output: str) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    for line in output.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        try:
            size = int(parts[0])
        except ValueError:
            continue
        rows.append({"path": parts[1], "size_bytes": size})
    return rows


def collect_df(paths: Iterable[str], runner: Runner = default_runner) -> list[dict[str, int | str]]:
    proc = runner(["df", "-B1", "-P", *paths])
    return parse_df(proc.stdout)


def collect_du(
    roots: Iterable[str],
    *,
    depth: int,
    runner: Runner = default_runner,
) -> tuple[list[dict[str, int | str]], list[str]]:
    rows: list[dict[str, int | str]] = []
    warnings: list[str] = []
    for root in roots:
        proc = runner(["du", "-x", "-B1", f"--max-depth={depth}", root])
        rows.extend(parse_du(proc.stdout))
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            warnings.append(f"du warning for {root}: {detail[:240]}")
    rows.sort(key=lambda row: int(row["size_bytes"]), reverse=True)
    return rows, warnings


def load_previous(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DiskReportError(f"invalid previous snapshot JSON: {path}") from exc


def growth_rows(current: list[dict], previous: dict | None) -> list[dict[str, int | str | bool]]:
    previous_sizes = {
        str(row.get("path")): int(row.get("size_bytes", 0))
        for row in (previous or {}).get("dirs", [])
        if row.get("path")
    }
    rows: list[dict[str, int | str | bool]] = []
    for row in current:
        path = str(row["path"])
        size = int(row["size_bytes"])
        old = previous_sizes.get(path)
        rows.append(
            {
                "path": path,
                "size_bytes": size,
                "previous_size_bytes": old if old is not None else 0,
                "growth_bytes": size - old if old is not None else size,
                "new_path": old is None,
            }
        )
    rows.sort(
        key=lambda row: (int(row["growth_bytes"]), int(row["size_bytes"])),
        reverse=True,
    )
    return rows


def proposal_for(path: str, size_bytes: int, growth_bytes: int) -> dict[str, str | int]:
    lower = path.lower()
    if lower.startswith("/backup") or "backup" in lower:
        action = "Review backup retention, verify an off-host copy, then move oldest redundant archives to quarantine before deletion."
        rollback = "Move quarantined archives back to their original backup path before deleting the quarantine."
    elif lower.startswith("/home") and ("/logs" in lower or "/tmp" in lower):
        action = "Review account-owned logs/tmp files, rotate or compress stale files, and quarantine before removal."
        rollback = "Restore quarantined files to the same account path and reload only the affected account service if needed."
    elif lower.startswith("/home") and "/mail" in lower:
        action = "Review mailbox retention with the account owner before compressing or archiving old mail."
        rollback = "Restore archived maildir content to the original account mailbox path."
    elif lower.startswith("/var/log") or "/log" in lower:
        action = "Tighten log rotation or journal retention after confirming no incident window needs the raw logs."
        rollback = "Restore logs from quarantine or backups; revert the rotation policy change."
    elif lower.startswith("/var/lib/mysql") or lower.startswith("/home") and "mysql" in lower:
        action = "Do not delete directly; inspect database/table growth and propose dump/archive only after application-owner review."
        rollback = "Restore from verified dump or database backup."
    else:
        action = "Inspect contents read-only, identify stale/generated files, then move candidates to quarantine before any delete."
        rollback = "Move quarantined files back to the original path."
    return {
        "path": path,
        "size_bytes": size_bytes,
        "growth_bytes": growth_bytes,
        "proposed_action": action,
        "rollback": rollback,
    }


def build_snapshot(
    repo_root: Path,
    roots: Iterable[str],
    *,
    depth: int,
    runner: Runner = default_runner,
) -> dict:
    roots = tuple(roots)
    evidence = fleet_evidence(repo_root)
    df_rows = collect_df(roots, runner)
    du_rows, warnings = collect_du(roots, depth=depth, runner=runner)
    return {
        "ts": _utc_now(),
        "spec_id": SPEC_ID,
        "decision_id": DECISION_ID,
        "host_target": TARGET_IP,
        "roots": list(roots),
        "depth": depth,
        "fleet_evidence": evidence,
        "df": df_rows,
        "dirs": du_rows,
        "warnings": warnings,
    }


def build_report(snapshot: dict, previous: dict | None, *, limit: int) -> dict:
    growth = growth_rows(snapshot["dirs"], previous)
    top_growth = growth[:limit]
    top_current = sorted(
        snapshot["dirs"],
        key=lambda row: int(row["size_bytes"]),
        reverse=True,
    )[:limit]
    proposals = [
        proposal_for(str(row["path"]), int(row["size_bytes"]), int(row["growth_bytes"]))
        for row in top_growth
    ]
    return {
        "ts": snapshot["ts"],
        "loop": REPORT_LOOP,
        "event": "reported",
        "cost": "$0",
        "spec_id": SPEC_ID,
        "decision_id": DECISION_ID,
        "host_target": TARGET_IP,
        "previous_snapshot_loaded": previous is not None,
        "df": snapshot["df"],
        "top_growth_dirs": top_growth,
        "top_current_dirs": top_current,
        "cleanup_proposals": proposals,
        "warnings": snapshot.get("warnings", []),
        "next": "Review proposed quarantine-first cleanup candidates; do not delete until a follow-up activation is explicitly approved.",
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# d147 209 Disk Growth Report",
        "",
        f"- Host: `{report['host_target']}`",
        f"- Generated: `{report['ts']}`",
        f"- Previous snapshot loaded: `{report['previous_snapshot_loaded']}`",
        f"- Action posture: read-only report; cleanup proposals only",
        "",
        "## Filesystems",
        "",
        "| mount | used | size | use |",
        "|---|---:|---:|---:|",
    ]
    for row in report["df"]:
        lines.append(
            f"| `{row['mounted_on']}` | {row['used_bytes']} | {row['size_bytes']} | {row['use_percent']}% |"
        )
    lines.extend(["", "## Top Growth Directories", "", "| path | growth_bytes | size_bytes |", "|---|---:|---:|"])
    for row in report["top_growth_dirs"]:
        marker = " new" if row.get("new_path") else ""
        lines.append(f"| `{row['path']}`{marker} | {row['growth_bytes']} | {row['size_bytes']} |")
    lines.extend(["", "## Reversible Cleanup Proposals", ""])
    for item in report["cleanup_proposals"]:
        lines.append(f"- `{item['path']}`: {item['proposed_action']} Rollback: {item['rollback']}")
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    lines.append("")
    return "\n".join(lines)


def append_ledger(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def run(
    repo_root: Path,
    *,
    roots: Iterable[str],
    depth: int,
    previous_snapshot: Path,
    snapshot_out: Path,
    report_json: Path,
    report_md: Path,
    ledger: Path,
    record: bool,
    require_target: bool,
    runner: Runner = default_runner,
) -> dict:
    ips = local_ips()
    if require_target and not on_target_host(ips):
        row = {
            "ts": _utc_now(),
            "loop": REPORT_LOOP,
            "event": "skipped",
            "detail": f"not on target host {TARGET_IP}; no disk survey run",
            "cost": "$0",
            "spec_id": SPEC_ID,
            "decision_id": DECISION_ID,
            "host_target": TARGET_IP,
            "local_ips": sorted(ips),
        }
        if record:
            append_ledger(ledger, row)
        return row

    previous = load_previous(previous_snapshot)
    snapshot = build_snapshot(repo_root, roots, depth=depth, runner=runner)
    report = build_report(snapshot, previous, limit=20)
    snapshot_out.parent.mkdir(parents=True, exist_ok=True)
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    snapshot_out.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_markdown(report), encoding="utf-8")
    if record:
        append_ledger(ledger, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=os.environ.get("FPAI_REPO_ROOT", "."))
    parser.add_argument("--root", action="append", dest="roots")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--previous-snapshot", default="/opt/fpai-build/state/d147_disk_209_snapshot.json")
    parser.add_argument("--snapshot-out", default="/opt/fpai-build/state/d147_disk_209_snapshot.json")
    parser.add_argument("--report-json", default="/opt/fpai-build/reports/d147_disk_209_report.json")
    parser.add_argument("--report-md", default="/opt/fpai-build/reports/d147_disk_209_report.md")
    parser.add_argument("--ops-ledger", default=os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--allow-off-target", action="store_true")
    args = parser.parse_args(argv)

    try:
        row = run(
            Path(args.repo_root).resolve(),
            roots=args.roots or DEFAULT_ROOTS,
            depth=args.depth,
            previous_snapshot=Path(args.previous_snapshot),
            snapshot_out=Path(args.snapshot_out),
            report_json=Path(args.report_json),
            report_md=Path(args.report_md),
            ledger=Path(args.ops_ledger),
            record=args.record,
            require_target=not args.allow_off_target,
        )
    except DiskReportError as exc:
        print(f"[d147] ERROR: {exc}", flush=True)
        return 1
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
