#!/usr/bin/env python3
"""Queue the assessment delivery proof verifier only when d193 is live.

This queue is intentionally local and reversible. It does not submit a lead,
send email, call Telegram, deploy code, read secrets, or append capability
learning. It only decides whether the existing proof verifier is allowed to run
against a real post-activation proof packet.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof


SPEC_ID = "SPEC_d211_auto-spot-topple-assessment-funn"
OPPORTUNITY_ID = "assessment-funnel-delivery-proof"
D193_SPEC_IDS = (
    *assessment_delivery_proof.D193_SPEC_IDS,
)
DEFAULT_QUEUE_FILE = Path("/opt/fpai-build/assessment_delivery_proof_queue.json")


def read_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "core" / "BUILD" / "REGISTRY.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def d193_merge_evidence(repo_root: Path, ops_ledger: Path) -> dict[str, Any]:
    registry = read_registry(repo_root)
    rows = registry.get("active_builds") if isinstance(registry, dict) else []
    registry_hits: list[dict[str, str]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        spec_id = str(row.get("id") or row.get("slug") or "").strip()
        if spec_id not in D193_SPEC_IDS:
            continue
        status = str(row.get("status") or "").strip().lower()
        registry_hits.append(
            {
                "spec_id": spec_id,
                "status": status,
                "branch": str(row.get("branch") or ""),
                "source": "registry",
            }
        )

    ops_hits: list[dict[str, str]] = []
    for row in activation_audit.read_jsonl(ops_ledger):
        event = str(row.get("event") or "").strip().lower()
        if event not in {"auto-merged", "backlog-merged", "merged"}:
            continue
        raw = json.dumps(row, sort_keys=True)
        matched = next((spec_id for spec_id in D193_SPEC_IDS if spec_id in raw), "")
        if matched:
            ops_hits.append(
                {
                    "spec_id": matched,
                    "event": event,
                    "detail": activation_audit.compact(str(row.get("detail") or ""))[:220],
                    "source": "ops_ledger",
                }
            )

    merged = any(hit["status"] == "merged" for hit in registry_hits) or bool(ops_hits)
    return {
        "ok": merged,
        "registry": registry_hits,
        "ops_ledger": ops_hits[:5],
    }


def d193_activation_evidence(repo_root: Path, ops_ledger: Path) -> dict[str, Any]:
    records = [
        activation_audit.BuildRecord(spec_id=spec_id, branch=f"build/{spec_id}") for spec_id in D193_SPEC_IDS
    ]
    audit = activation_audit.audit(repo_root, ops_ledger=ops_ledger, records=records)
    rows = audit.get("rows") if isinstance(audit, dict) else []
    evidence: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        activation = list(row.get("activation_evidence") or [])
        if activation:
            evidence.append(
                {
                    "spec_id": row.get("spec_id", ""),
                    "classification": row.get("classification", ""),
                    "activation_evidence": activation,
                }
            )
    return {
        "ok": bool(evidence),
        "evidence": evidence,
        "unexplained_inert_count": audit.get("unexplained_inert_count", 0),
    }


def build_queue_packet(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    merged = d193_merge_evidence(repo_root, ops_ledger)
    activation = d193_activation_evidence(repo_root, ops_ledger)
    ready = merged["ok"] and activation["ok"]
    missing: list[str] = []
    if not merged["ok"]:
        missing.append("d193_merged")
    if not activation["ok"]:
        missing.append("d193_activation_evidence")

    verifier_command = [
        "python3",
        "tools/build_loop/assessment_delivery_proof.py",
        "--repo-root",
        str(repo_root),
        "--ops-ledger",
        str(ops_ledger),
        "--proof-file",
        proof_file_placeholder,
        "--proof-log",
        str(proof_log),
        "--capability-ledger",
        str(capability_ledger_path),
        "--append-capability",
        "--json",
    ]
    return {
        "schema": "assessment_delivery_proof_queue.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "opportunity_id": OPPORTUNITY_ID,
        "status": "ready" if ready else "hold",
        "missing": missing,
        "d193": {
            "merged": merged,
            "activation": activation,
        },
        "verifier": {
            "script": "tools/build_loop/assessment_delivery_proof.py",
            "command": verifier_command,
            "required_proof_fields": [
                "real_execution=true",
                "lens=life",
                "response.ok=true",
                "response.deliverable_status=queued",
                "recipient_email.status sent/delivered/success",
                "founder_alert status/ok",
                "page_acknowledgement contains Allocation Score inbox acknowledgement",
                "learning non-empty",
                "sandbox_only absent/false",
            ],
        },
        "learning_policy": (
            "Append to the d185 capability-created ledger only through the verifier, "
            "only with --append-capability, and only after pass."
        ),
        "guardrails": {
            "live_submit_performed": False,
            "email_send_performed_by_queue": False,
            "telegram_send_performed_by_queue": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "marginal_cost_usd": 0,
        },
    }


def write_packet(path: Path, packet: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--ops-ledger", type=Path, default=activation_audit.DEFAULT_OPS_LEDGER)
    parser.add_argument("--queue-file", type=Path, default=DEFAULT_QUEUE_FILE)
    parser.add_argument("--proof-log", type=Path, default=assessment_delivery_proof.DEFAULT_PROOF_LOG)
    parser.add_argument("--capability-ledger", type=Path, default=capability_ledger.DEFAULT_LEDGER)
    parser.add_argument("--proof-file-placeholder", default="<packet.json>")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    packet = build_queue_packet(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_packet(args.queue_file, packet)

    if args.json:
        print(json.dumps(packet, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof-queue: {packet['status']}")
    return 0 if packet["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
