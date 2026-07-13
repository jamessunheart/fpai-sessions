#!/usr/bin/env python3
"""Write the d217 readiness assessment for assessment funnel delivery proof.

This is a reversible local verifier/spec artifact. It composes the d216
delivery-proof wrapper, which composes the d215 proof spec, d214 docket, d213
manifest, d212 runbook, d211 queue, and d210 verifier. It does not submit
leads, send email, call Telegram, deploy, read secrets, append capability
learning, push, merge, or spend money.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof, assessment_delivery_proof_delivery


SPEC_ID = "SPEC_d217_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
SOURCE_DECISION = "d217"
SOURCE_TIMESTAMP = "2026-07-13T16:08:20Z"
OPPORTUNITY_ID = assessment_delivery_proof_delivery.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 86.4
UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE = 34
DEFAULT_ASSESSMENT_FILE = Path("/opt/fpai-build/assessment_delivery_proof_assessment.json")
DEFAULT_MARKDOWN_FILE = Path("/opt/fpai-build/assessment_delivery_proof_assessment.md")


def build_delivery_proof_assessment(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<real-proof-packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    delivery = assessment_delivery_proof_delivery.build_delivery_proof(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    status = "ready" if delivery.get("status") == "ready" else "hold"
    activation_gate = (
        delivery.get("activation_gate") if isinstance(delivery.get("activation_gate"), dict) else {}
    )
    commands = delivery.get("commands") if isinstance(delivery.get("commands"), dict) else {}

    return {
        "schema": "assessment_delivery_proof_assessment.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_decision": SOURCE_DECISION,
        "source_spec_id": SOURCE_SPEC_ID,
        "source_timestamp": SOURCE_TIMESTAMP,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "activation_audit_unexplained_inert_count_before_queue": UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE,
        "status": status,
        "missing": list(delivery.get("missing") or []),
        "assessment_authority": {
            "local_readiness_assessment_only": True,
            "operator_may_collect_one_real_proof_packet_after_ready": status == "ready",
            "requires_d193_merged": True,
            "requires_d182_d188_activation_evidence": True,
            "proof_must_be_real": True,
            "sandbox_proof_counts": False,
            "assessment_artifact_counts_as_topple": False,
        },
        "activation_gate": {
            "d193_activation_ok": bool(activation_gate.get("d193_activation_ok")),
            "uses_d182_d188_evidence": bool(activation_gate.get("uses_d182_d188_evidence")),
            "unexplained_inert_count": activation_gate.get("unexplained_inert_count", 0),
        },
        "evidence_bundle_required": _evidence_bundle_required(),
        "readiness_assessment": _readiness_assessment(status),
        "operator_steps": _operator_steps(status),
        "commands": {
            "delivery_proof": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_delivery.py",
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
            "proof_spec": list(commands.get("proof_spec") or []),
            "docket": list(commands.get("docket") or []),
            "manifest": list(commands.get("manifest") or []),
            "queue": list(commands.get("queue") or []),
            "runbook": list(commands.get("runbook") or []),
            "verifier": list(commands.get("verifier") or []),
        },
        "proof_packet_template": delivery.get("proof_packet_template", {}),
        "delivery_proof": delivery,
        "do_not_count_toppled_until": _count_toppled_requirements(delivery),
        "learning_policy": (
            "Append d185 capability-created learning only through the d210 verifier, "
            "only with --append-capability, and only after one real proof packet passes."
        ),
        "guardrails": {
            "live_submit_performed_by_assessment": False,
            "email_send_performed_by_assessment": False,
            "telegram_send_performed_by_assessment": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_assessment": False,
            "marginal_cost_usd": 0,
        },
    }


def _evidence_bundle_required() -> dict[str, str]:
    return {
        "activation": "d193 merged plus d182/d188 guarded activation evidence",
        "lead": "one controlled real Life assessment lead submitted through the activated path",
        "recipient_email_delivery_status": "sent, delivered, queued_and_sent, success, or ok=true",
        "founder_alert_status": "sent, delivered, queued_and_sent, success, ok=true, or response founder_alert ok=true",
        "page_acknowledgement": assessment_delivery_proof.REQUIRED_RESPONSE_ACK,
        "learning": "non-empty capability-ledger learning derived from the real execution",
        "verifier": "assessment_delivery_proof.py returns status=pass with --append-capability",
    }


def _readiness_assessment(status: str) -> dict[str, Any]:
    return {
        "ready_to_collect_real_proof": status == "ready",
        "ready_to_count_toppled": False,
        "reason": (
            "d193 merge and guarded activation evidence are present; collect exactly one real proof packet."
            if status == "ready"
            else "Hold until d193 merge evidence and guarded activation evidence are both present."
        ),
        "topple_count_policy": "Only a passing d210 verifier row with capability-ledger append can count this domino toppled.",
    }


def _operator_steps(status: str) -> list[str]:
    if status != "ready":
        return [
            "Hold. This readiness assessment is not executable until d193 merge evidence and guarded activation evidence are both present.",
            "Re-run this assessment after d193 is merged and d182/d188 activation evidence is visible.",
            "Do not submit a lead, send email, send founder alerts, or append capability learning from this held artifact.",
        ]
    return [
        "Collect exactly one controlled real Life assessment lead through the activated assessment path.",
        "Capture page acknowledgement, API response, recipient email delivery status, and founder alert status.",
        "Write the proof packet using the template in this assessment artifact.",
        "Run the verifier command with --append-capability.",
        "Count the domino toppled only if the verifier returns status=pass and appends d185 capability learning.",
    ]


def _count_toppled_requirements(delivery: dict[str, Any]) -> list[str]:
    requirements = list(delivery.get("do_not_count_toppled_until") or [])
    if "d217 readiness assessment status=ready" not in requirements:
        requirements.insert(0, "d217 readiness assessment status=ready")
    return requirements


def render_markdown(assessment: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof Readiness Assessment",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{assessment['spec_id']}`",
        f"- Source: `{assessment['source_spec_id']}` at `{assessment['source_timestamp']}`",
        f"- Opportunity: `{assessment['opportunity_id']}`",
        f"- Status: `{assessment['status']}`",
        f"- Missing: `{', '.join(assessment.get('missing') or []) or 'none'}`",
        f"- Next domino score: `{assessment['next_domino_score']}`",
        "",
        "## Assessment Authority",
    ]
    for key, value in sorted((assessment.get("assessment_authority") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Evidence Bundle Required"])
    for key, value in (assessment.get("evidence_bundle_required") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Readiness Assessment"])
    for key, value in (assessment.get("readiness_assessment") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Operator Steps"])
    for index, step in enumerate(assessment.get("operator_steps") or [], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Verifier Command", "", "```bash"])
    lines.append(" ".join(str(part) for part in assessment.get("commands", {}).get("verifier") or []))
    lines.extend(["```", "", "## Do Not Count Toppled Until"])
    for item in assessment.get("do_not_count_toppled_until") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Guardrails"])
    for key, value in sorted((assessment.get("guardrails") or {}).items()):
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
    parser.add_argument("--assessment-file", type=Path, default=DEFAULT_ASSESSMENT_FILE)
    parser.add_argument("--markdown-file", type=Path, default=DEFAULT_MARKDOWN_FILE)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    assessment = build_delivery_proof_assessment(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.assessment_file, assessment)
        write_markdown(args.markdown_file, assessment)

    if args.json:
        print(json.dumps(assessment, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof-assessment: {assessment['status']}")
    return 0 if assessment["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
