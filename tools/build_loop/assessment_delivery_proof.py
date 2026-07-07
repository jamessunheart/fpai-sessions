#!/usr/bin/env python3
"""Verify d210 assessment funnel delivery proof.

This verifier is intentionally local and evidence-driven. It does not submit a
lead, send mail, call Telegram, deploy, or touch secrets. It validates a real
post-activation proof packet and appends d185 capability learning only when all
required proof fields are defensible.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit


SPEC_ID = "SPEC_d210_auto-spot-topple-assessment-funn"
D193_SPEC_ID = "SPEC_d193_spec-d193-wire-the-assessment-fu"
D193_SPEC_IDS = (D193_SPEC_ID, "SPEC_d193_wire-assessment-funnel-auto-deliver")
DEFAULT_PROOF_LOG = Path("/opt/fpai-build/assessment_delivery_proof.jsonl")
REQUIRED_RESPONSE_ACK = "Allocation Score is on its way to your inbox"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read proof file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"proof file is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("proof file must be a JSON object")
    return data


def d193_activation_evidence(repo_root: Path, ops_ledger: Path) -> dict[str, Any]:
    records = [activation_audit.BuildRecord(spec_id=spec_id, branch=f"build/{spec_id}") for spec_id in D193_SPEC_IDS]
    audit = activation_audit.audit(repo_root, ops_ledger=ops_ledger, records=records)
    matched_rows = [
        row for row in audit.get("rows", []) if isinstance(row, dict) and list(row.get("activation_evidence") or [])
    ]
    evidence = [item for row in matched_rows for item in list(row.get("activation_evidence") or [])]
    return {
        "ok": bool(evidence),
        "classification": ", ".join(str(row.get("classification", "")) for row in matched_rows),
        "evidence": evidence[:5],
        "unexplained_inert_count": audit.get("unexplained_inert_count", 0),
    }


def validate_proof_packet(packet: dict[str, Any], *, require_real: bool = True) -> dict[str, Any]:
    response = _as_dict(packet.get("response"))
    recipient = _as_dict(packet.get("recipient_email"))
    founder = _as_dict(packet.get("founder_alert"))
    page = _as_dict(packet.get("page_acknowledgement"))

    checks = {
        "life_lead": _is_life_lead(packet),
        "response_ok": response.get("ok") is True,
        "deliverable_queued": str(response.get("deliverable_status") or "").lower() == "queued",
        "recipient_email_sent": _status_is_success(recipient),
        "founder_alert_sent": _founder_success(founder, response),
        "page_acknowledged": _page_acknowledged(page, response),
        "capability_learning_present": bool(str(packet.get("learning") or "").strip()),
    }
    if require_real:
        checks["real_execution_declared"] = _truthy(packet.get("real_execution"))
        checks["non_sandbox_proof"] = not _truthy(packet.get("sandbox_only"))

    missing = [name for name, ok in checks.items() if not ok]
    return {
        "ok": not missing,
        "checks": checks,
        "missing": missing,
        "summary": _proof_summary(packet, response, recipient, founder, page),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "real"}


def _is_life_lead(packet: dict[str, Any]) -> bool:
    lens = str(packet.get("lens") or packet.get("assessment_lens") or "").lower()
    interest = str(packet.get("interest") or "").lower()
    return lens == "life" or interest == "life-assessment"


def _status_is_success(section: dict[str, Any]) -> bool:
    status = str(section.get("status") or section.get("detail") or "").lower()
    return status in {"sent", "delivered", "queued_and_sent", "success"} or section.get("ok") is True


def _founder_success(founder: dict[str, Any], response: dict[str, Any]) -> bool:
    if _status_is_success(founder):
        return True
    response_alert = response.get("founder_alert")
    if isinstance(response_alert, dict):
        return response_alert.get("ok") is True
    return False


def _page_acknowledged(page: dict[str, Any], response: dict[str, Any]) -> bool:
    message = " ".join(str(page.get(key) or "") for key in ("message", "text", "acknowledgement"))
    return bool(re.search(re.escape(REQUIRED_RESPONSE_ACK), message, re.IGNORECASE))


def _proof_summary(
    packet: dict[str, Any],
    response: dict[str, Any],
    recipient: dict[str, Any],
    founder: dict[str, Any],
    page: dict[str, Any],
) -> dict[str, Any]:
    return {
        "lead_email": packet.get("lead_email") or packet.get("email") or "",
        "lead_file": response.get("filename") or packet.get("lead_file") or "",
        "recipient_email_status": recipient.get("status") or recipient.get("detail") or "",
        "founder_alert_status": founder.get("status") or founder.get("detail") or response.get("founder_alert") or "",
        "page_acknowledgement": page.get("message") or response.get("message") or "",
        "learning": packet.get("learning") or "",
    }


def build_result_row(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_packet: dict[str, Any],
    proof_path: Path,
    append_capability: bool,
    capability_path: Path,
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or utc_now()
    activation = d193_activation_evidence(repo_root, ops_ledger)
    proof = validate_proof_packet(proof_packet)
    status = "pass" if activation["ok"] and proof["ok"] else "hold"
    row = {
        "schema": "assessment_delivery_proof.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "status": status,
        "activation": activation,
        "proof": proof,
        "proof_file": str(proof_path),
        "capability_ledger_appended": False,
        "capability_ledger": str(capability_path),
        "guardrails": {
            "live_submit_performed": False,
            "email_send_performed_by_verifier": False,
            "telegram_send_performed_by_verifier": False,
            "marginal_cost_usd": 0,
        },
    }
    if status == "pass" and append_capability:
        cap_row = capability_ledger.capability_row(
            source_type="proof",
            source_id=SPEC_ID,
            title="Assessment funnel delivery proof",
            scores={"trust": 1, "knowledge_gained": 1, "automation": 1},
            reusable_intelligence="tools/build_loop/assessment_delivery_proof.py",
            basis=(
                "Real d193 Life assessment proof packet verified recipient email delivery, "
                "founder alert, page acknowledgement, and capability learning."
            ),
            reviewed_by="d210 local verifier",
            ts=stamp,
        )
        capability_ledger.append_row(capability_path, cap_row)
        row["capability_ledger_appended"] = True
        row["capability_row"] = cap_row
    elif append_capability:
        row["capability_append_held_reason"] = "proof is incomplete or d193 activation evidence is missing"
    return row


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--ops-ledger", type=Path, default=activation_audit.DEFAULT_OPS_LEDGER)
    parser.add_argument("--proof-file", type=Path, required=True)
    parser.add_argument("--proof-log", type=Path, default=DEFAULT_PROOF_LOG)
    parser.add_argument("--capability-ledger", type=Path, default=capability_ledger.DEFAULT_LEDGER)
    parser.add_argument("--append-capability", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        packet = load_json(args.proof_file)
        row = build_result_row(
            repo_root=args.repo_root,
            ops_ledger=args.ops_ledger,
            proof_packet=packet,
            proof_path=args.proof_file,
            append_capability=args.append_capability,
            capability_path=args.capability_ledger,
        )
    except ValueError as exc:
        row = {
            "schema": "assessment_delivery_proof.v1",
            "ts": utc_now(),
            "spec_id": SPEC_ID,
            "status": "error",
            "error": str(exc),
            "proof_file": str(args.proof_file),
        }

    append_jsonl(args.proof_log, row)
    if args.json:
        print(json.dumps(row, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof: {row['status']}")
    return 0 if row.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
