#!/usr/bin/env python3
"""Write the d216 delivery-proof wrapper for assessment funnel proof.

This is a reversible local verifier/spec artifact. It composes the d215 proof
spec, which composes the d214 docket, d213 manifest, d212 runbook, d211 queue,
and d210 verifier. It does not submit leads, send email, call Telegram, deploy,
read secrets, append capability learning, push, merge, or spend money.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof, assessment_delivery_proof_spec


SPEC_ID = "SPEC_d216_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
SOURCE_DECISION = "d216"
SOURCE_TIMESTAMP = "2026-07-12T16:07:56Z"
OPPORTUNITY_ID = assessment_delivery_proof_spec.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 84.4
UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE = 34
DEFAULT_DELIVERY_FILE = Path("/opt/fpai-build/assessment_delivery_proof_delivery.json")
DEFAULT_MARKDOWN_FILE = Path("/opt/fpai-build/assessment_delivery_proof_delivery.md")


def build_delivery_proof(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<real-proof-packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    proof_spec = assessment_delivery_proof_spec.build_delivery_proof_spec(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    status = "ready" if proof_spec.get("status") == "ready" else "hold"
    activation_gate = (
        proof_spec.get("activation_gate") if isinstance(proof_spec.get("activation_gate"), dict) else {}
    )
    commands = proof_spec.get("commands") if isinstance(proof_spec.get("commands"), dict) else {}

    return {
        "schema": "assessment_delivery_proof_delivery.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_decision": SOURCE_DECISION,
        "source_spec_id": SOURCE_SPEC_ID,
        "source_timestamp": SOURCE_TIMESTAMP,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "activation_audit_unexplained_inert_count_before_queue": UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE,
        "status": status,
        "missing": list(proof_spec.get("missing") or []),
        "delivery_authority": {
            "local_delivery_proof_only": True,
            "operator_may_run_one_real_lead_after_ready": status == "ready",
            "requires_d193_merged": True,
            "requires_d182_d188_activation_evidence": True,
            "proof_must_be_real": True,
            "sandbox_proof_counts": False,
        },
        "activation_gate": {
            "d193_activation_ok": bool(activation_gate.get("d193_activation_ok")),
            "uses_d182_d188_evidence": bool(activation_gate.get("uses_d182_d188_evidence")),
            "unexplained_inert_count": activation_gate.get("unexplained_inert_count", 0),
        },
        "proof_required": {
            "lead": "one controlled real Life assessment lead",
            "recipient_email_delivery_status": "required",
            "founder_alert_status": "required",
            "page_acknowledgement": assessment_delivery_proof.REQUIRED_RESPONSE_ACK,
            "capability_ledger_learning": "required; appended only by verifier after pass",
            "verifier_pass": "assessment_delivery_proof.py status=pass",
        },
        "operator_steps": _operator_steps(status),
        "commands": {
            "proof_spec": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_spec.py",
                "--repo-root",
                str(repo_root),
                "--ops-ledger",
                str(ops_ledger),
                "--proof-log",
                str(proof_log),
                "--capability-ledger",
                str(capability_ledger_path),
                "--proof-file-placeholder",
                proof_file_placeholder,
                "--json",
            ],
            "docket": list(commands.get("docket") or []),
            "manifest": list(commands.get("manifest") or []),
            "queue": list(commands.get("queue") or []),
            "runbook": list(commands.get("runbook") or []),
            "verifier": list(commands.get("verifier") or []),
        },
        "proof_packet_template": proof_spec.get("proof_packet_template", {}),
        "proof_spec": proof_spec,
        "do_not_count_toppled_until": _count_toppled_requirements(proof_spec),
        "learning_policy": (
            "Append d185 capability-created learning only through the d210 verifier, "
            "only with --append-capability, and only after one real proof packet passes."
        ),
        "guardrails": {
            "live_submit_performed_by_delivery_proof": False,
            "email_send_performed_by_delivery_proof": False,
            "telegram_send_performed_by_delivery_proof": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_delivery_proof": False,
            "marginal_cost_usd": 0,
        },
    }


def _operator_steps(status: str) -> list[str]:
    if status != "ready":
        return [
            "Hold. This delivery proof is not executable until d193 merge evidence and guarded activation evidence are both present.",
            "Re-run this delivery-proof generator after d193 is merged and d182/d188 activation evidence is visible.",
            "Do not submit a lead, send email, send founder alerts, or append capability learning from this held artifact.",
        ]
    return [
        "Submit exactly one controlled real Life assessment lead through the activated assessment path.",
        "Capture page acknowledgement, API response, recipient email delivery status, and founder alert status.",
        "Write the proof packet using the template in this artifact.",
        "Run the verifier command with --append-capability.",
        "Count the domino toppled only if the verifier returns status=pass and appends d185 capability learning.",
    ]


def _count_toppled_requirements(proof_spec: dict[str, Any]) -> list[str]:
    requirements = list(proof_spec.get("do_not_count_toppled_until") or [])
    if "d216 delivery proof status=ready" not in requirements:
        requirements.insert(0, "d216 delivery proof status=ready")
    return requirements


def render_markdown(delivery: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{delivery['spec_id']}`",
        f"- Source: `{delivery['source_spec_id']}` at `{delivery['source_timestamp']}`",
        f"- Opportunity: `{delivery['opportunity_id']}`",
        f"- Status: `{delivery['status']}`",
        f"- Missing: `{', '.join(delivery.get('missing') or []) or 'none'}`",
        f"- Next domino score: `{delivery['next_domino_score']}`",
        "",
        "## Delivery Authority",
    ]
    for key, value in sorted((delivery.get("delivery_authority") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Proof Required"])
    for key, value in (delivery.get("proof_required") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Operator Steps"])
    for index, step in enumerate(delivery.get("operator_steps") or [], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Verifier Command", "", "```bash"])
    lines.append(" ".join(str(part) for part in delivery.get("commands", {}).get("verifier") or []))
    lines.extend(["```", "", "## Do Not Count Toppled Until"])
    for item in delivery.get("do_not_count_toppled_until") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Guardrails"])
    for key, value in sorted((delivery.get("guardrails") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--ops-ledger", type=Path, default=activation_audit.DEFAULT_OPS_LEDGER)
    parser.add_argument("--proof-log", type=Path, default=assessment_delivery_proof.DEFAULT_PROOF_LOG)
    parser.add_argument("--capability-ledger", type=Path, default=capability_ledger.DEFAULT_LEDGER)
    parser.add_argument("--proof-file-placeholder", default="<real-proof-packet.json>")
    parser.add_argument("--delivery-file", type=Path, default=DEFAULT_DELIVERY_FILE)
    parser.add_argument("--markdown-file", type=Path, default=DEFAULT_MARKDOWN_FILE)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    delivery = build_delivery_proof(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.delivery_file, delivery)
        write_markdown(args.markdown_file, delivery)

    if args.json:
        print(json.dumps(delivery, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof: {delivery['status']}")
    return 0 if delivery["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
