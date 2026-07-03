#!/usr/bin/env python3
"""Retire local Postfix on host 198 after Brevo outbound coverage is evidenced."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SPEC_ID = "SPEC_d145_self-audit-infra-retire-postfix"
DECISION_ID = "d145"
TARGET_IP = "198.54.123.234"
SERVICE = "postfix"
ROLLBACK = "systemctl enable --now postfix"


class RetireError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RetireError(f"missing evidence file: {path}") from exc


def brevo_evidence(repo_root: Path) -> list[str]:
    """Return repo evidence that outbound mail is covered by Brevo."""
    inventory = repo_root / "core" / "STATE" / "RESOURCE_INVENTORY.md"
    text = _read_text(inventory)
    evidence: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if "brevo" in lowered and ("send" in lowered or "outbound" in lowered):
            evidence.append(line.strip())
    if not evidence:
        raise RetireError(
            "Brevo outbound evidence not found in core/STATE/RESOURCE_INVENTORY.md"
        )
    return evidence


def local_ips() -> set[str]:
    override = os.environ.get("FPAI_POSTFIX_RETIRE_HOST_IPS")
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


def systemctl_cmd() -> str:
    return os.environ.get("SYSTEMCTL", "systemctl")


def service_state(verb: str) -> str:
    proc = subprocess.run(
        [systemctl_cmd(), verb, SERVICE],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    value = (proc.stdout or proc.stderr).strip()
    return value or f"exit:{proc.returncode}"


def stop_disable() -> None:
    proc = subprocess.run(
        [systemctl_cmd(), "disable", "--now", SERVICE],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RetireError(f"systemctl disable --now postfix failed: {detail}")


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
) -> dict:
    return {
        "ts": _utc_now(),
        "loop": "infra-retire-postfix",
        "event": event,
        "detail": detail,
        "cost": "$0",
        "artifact": "core/BUILD/activate/SPEC_d145_self-audit-infra-retire-postfix.sh",
        "next": "Rollback with: systemctl enable --now postfix",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "spec_id": SPEC_ID,
        "decision_id": DECISION_ID,
        "host_target": TARGET_IP,
        "service": SERVICE,
        "rollback": ROLLBACK,
        "brevo_evidence": evidence,
        "local_ips": sorted(set(target_ips)),
        "before": before or {},
        "after": after or {},
    }


def run(repo_root: Path, ledger: Path, execute: bool) -> dict:
    evidence = brevo_evidence(repo_root)
    ips = local_ips()
    if not on_target_host(ips):
        row = build_row(
            event="skipped",
            detail=f"not on target host {TARGET_IP}; no postfix action taken",
            evidence=evidence,
            target_ips=ips,
        )
        if execute:
            append_ledger(ledger, row)
        return row

    before = {
        "active": service_state("is-active"),
        "enabled": service_state("is-enabled"),
    }
    if execute:
        stop_disable()
        event = "succeeded"
        detail = "postfix stopped and disabled on target host"
    else:
        event = "proposed"
        detail = "dry-run: postfix would be stopped and disabled on target host"
    after = {
        "active": service_state("is-active"),
        "enabled": service_state("is-enabled"),
    }
    row = build_row(
        event=event,
        detail=detail,
        evidence=evidence,
        target_ips=ips,
        before=before,
        after=after,
    )
    if execute:
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
    args = parser.parse_args(argv)

    try:
        row = run(Path(args.repo_root).resolve(), Path(args.ops_ledger), args.execute)
    except RetireError as exc:
        print(f"[d145] ERROR: {exc}", flush=True)
        return 1
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
