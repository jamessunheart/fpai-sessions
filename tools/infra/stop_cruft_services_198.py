#!/usr/bin/env python3
"""Stop d146 cruft services on host 198 behind an explicit reversible flag."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SPEC_ID = "SPEC_d146_self-audit-infra-cruft-services"
DECISION_ID = "d146"
TARGET_IP = "198.54.123.234"
SERVICES = ("fpai-cocoon.service", "whaletrack-magnet.service")
FLAG_ENV = "FPAI_D146_CRUFT_STOP"
ROLLBACK = "systemctl enable --now fpai-cocoon.service whaletrack-magnet.service"


class CruftStopError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CruftStopError(f"missing evidence file: {path}") from exc


def fleet_evidence(repo_root: Path) -> list[str]:
    """Return FLEET_SNAPSHOT lines that authorize this narrow cleanup."""
    snapshot = repo_root / "core" / "STATE" / "FLEET_SNAPSHOT.md"
    text = _read_text(snapshot)
    evidence: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if "198" in lowered and ("ram" in lowered or "swap" in lowered):
            evidence.append(line.strip())
        elif "cruft" in lowered and "cocoon" in lowered and "whaletrack-magnet" in lowered:
            evidence.append(line.strip())
    if not any(
        "cruft" in line.lower()
        and "cocoon" in line.lower()
        and "whaletrack-magnet" in line.lower()
        for line in evidence
    ):
        raise CruftStopError(
            "d146 cruft evidence not found in core/STATE/FLEET_SNAPSHOT.md"
        )
    return evidence


def local_ips() -> set[str]:
    override = os.environ.get("FPAI_D146_HOST_IPS")
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


def flag_enabled() -> bool:
    return os.environ.get(FLAG_ENV) == "1"


def systemctl_cmd() -> str:
    return os.environ.get("SYSTEMCTL", "systemctl")


def service_state(service: str, verb: str) -> str:
    proc = subprocess.run(
        [systemctl_cmd(), verb, service],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    value = (proc.stdout or proc.stderr).strip()
    return value or f"exit:{proc.returncode}"


def service_snapshot() -> dict[str, dict[str, str]]:
    return {
        service: {
            "active": service_state(service, "is-active"),
            "enabled": service_state(service, "is-enabled"),
        }
        for service in SERVICES
    }


def stop_disable_services() -> None:
    proc = subprocess.run(
        [systemctl_cmd(), "disable", "--now", *SERVICES],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise CruftStopError(f"systemctl disable --now cruft services failed: {detail}")


def meminfo_path() -> Path:
    return Path(os.environ.get("FPAI_D146_MEMINFO", "/proc/meminfo"))


def memory_snapshot() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in _read_text(meminfo_path()).splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            key = parts[0].removesuffix(":")
            if key in {"MemTotal", "MemFree", "MemAvailable", "SwapTotal", "SwapFree"}:
                try:
                    values[key] = int(parts[1])
                except ValueError:
                    continue
    if "MemAvailable" not in values:
        raise CruftStopError(f"MemAvailable not found in {meminfo_path()}")
    return values


def ram_reclaimed_kib(before: dict[str, int], after: dict[str, int]) -> int:
    return after.get("MemAvailable", 0) - before.get("MemAvailable", 0)


def append_ledger(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def build_row(
    *,
    event: str,
    detail: str,
    evidence: list[str],
    target_ips: Iterable[str],
    before: dict | None = None,
    after: dict | None = None,
    memory_before: dict | None = None,
    memory_after: dict | None = None,
) -> dict:
    memory_before = memory_before or {}
    memory_after = memory_after or {}
    return {
        "ts": _utc_now(),
        "loop": "infra-stop-cruft-services",
        "event": event,
        "detail": detail,
        "cost": "$0",
        "artifact": "core/BUILD/activate/SPEC_d146_self-audit-infra-cruft-services.sh",
        "next": f"Rollback with: {ROLLBACK}",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "spec_id": SPEC_ID,
        "decision_id": DECISION_ID,
        "host_target": TARGET_IP,
        "services": list(SERVICES),
        "rollback": ROLLBACK,
        "flag_env": FLAG_ENV,
        "flag_enabled": flag_enabled(),
        "fleet_evidence": evidence,
        "local_ips": sorted(set(target_ips)),
        "before": before or {},
        "after": after or {},
        "memory_before": memory_before,
        "memory_after": memory_after,
        "ram_reclaimed_kib": (
            ram_reclaimed_kib(memory_before, memory_after)
            if memory_before and memory_after
            else 0
        ),
    }


def run(
    repo_root: Path,
    ledger: Path,
    *,
    execute: bool,
    record: bool,
    settle_seconds: float,
) -> dict:
    evidence = fleet_evidence(repo_root)
    ips = local_ips()
    if not on_target_host(ips):
        row = build_row(
            event="skipped",
            detail=f"not on target host {TARGET_IP}; no cruft service action taken",
            evidence=evidence,
            target_ips=ips,
        )
        if record:
            append_ledger(ledger, row)
        return row

    before = service_snapshot()
    memory_before = memory_snapshot()

    if execute and flag_enabled():
        stop_disable_services()
        if settle_seconds > 0:
            time.sleep(settle_seconds)
        event = "succeeded"
        detail = "cocoon and whaletrack-magnet stopped and disabled on target host"
    elif execute:
        event = "flag_disabled"
        detail = f"{FLAG_ENV}=1 not set; no cruft service action taken"
    else:
        event = "proposed"
        detail = "dry-run: cocoon and whaletrack-magnet would be stopped and disabled"

    after = service_snapshot()
    memory_after = memory_snapshot()
    row = build_row(
        event=event,
        detail=detail,
        evidence=evidence,
        target_ips=ips,
        before=before,
        after=after,
        memory_before=memory_before,
        memory_after=memory_after,
    )
    if record:
        append_ledger(ledger, row)
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=os.environ.get("FPAI_REPO_ROOT", "."))
    parser.add_argument(
        "--ops-ledger",
        default=os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"),
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--settle-seconds", type=float, default=5.0)
    args = parser.parse_args(argv)

    try:
        row = run(
            Path(args.repo_root).resolve(),
            Path(args.ops_ledger),
            execute=args.execute,
            record=args.record,
            settle_seconds=args.settle_seconds,
        )
    except CruftStopError as exc:
        print(f"[d146] ERROR: {exc}", flush=True)
        return 1
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
