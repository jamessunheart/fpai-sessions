#!/usr/bin/env python3
"""Write the d220 verification queue for assessment funnel delivery proof.

This is a reversible local verifier/spec artifact. It composes the d219
execution spec, which composes the d218 verifier/spec and the d210-d217
verifier chain. It does not submit leads, send email, call Telegram, deploy,
read secrets, append capability learning, push, merge, or spend money.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof, assessment_delivery_proof_execution_spec


SPEC_ID = "SPEC_d220_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
SOURCE_DECISION = "d220"
SOURCE_TIMESTAMP = "2026-07-16T16:09:37Z"
OPPORTUNITY_ID = assessment_delivery_proof_execution_spec.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 91.4
UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE = 34
DEFAULT_VERIFICATION_QUEUE_FILE = Path("/opt/fpai-build/assessment_delivery_proof_verification_queue.json")
DEFAULT_MARKDOWN_FILE = Path("/opt/fpai-build/assessment_delivery_proof_verification_queue.md")


def build_verification_queue(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<real-proof-packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    execution_spec = assessment_delivery_proof_execution_spec.build_execution_spec(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    status = "ready" if execution_spec.get("status") == "ready" else "hold"
    commands = execution_spec.get("commands") if isinstance(execution_spec.get("commands"), dict) else {}
    activation_gate = (
        execution_spec.get("activation_gate") if isinstance(execution_spec.get("activation_gate"), dict) else {}
    )

    return {
        "schema": "assessment_delivery_proof_verification_queue.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_decision": SOURCE_DECISION,
        "source_spec_id": SOURCE_SPEC_ID,
        "source_timestamp": SOURCE_TIMESTAMP,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "activation_audit_unexplained_inert_count_before_queue": UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE,
        "status": status,
        "missing": list(execution_spec.get("missing") or []),
        "verification_queue_authority": {
            "local_verifier_spec_only": True,
            "queued_for_real_execution_after_ready": status == "ready",
            "operator_may_submit_one_controlled_life_lead_after_ready": status == "ready",
            "operator_may_run_verifier_after_real_proof_packet": status == "ready",
            "requires_d193_merged": True,
            "requires_d182_d188_activation_evidence": True,
            "requires_real_recipient_delivery_status": True,
            "requires_real_founder_alert_status": True,
            "requires_page_acknowledgement": True,
            "requires_capability_ledger_learning": True,
            "sandbox_proof_counts": False,
            "queue_artifact_counts_as_topple": False,
        },
        "activation_gate": {
            "d193_activation_ok": bool(activation_gate.get("d193_activation_ok")),
            "uses_d182_d188_evidence": bool(activation_gate.get("uses_d182_d188_evidence")),
            "unexplained_inert_count": activation_gate.get("unexplained_inert_count", 0),
        },
        "delivery_status_contract": _delivery_status_contract(),
        "queue_gate": _queue_gate(status),
        "operator_steps": _operator_steps(status),
        "commands": {
            "execution_spec": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_execution_spec.py",
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
            "verifier_spec": list(commands.get("verifier_spec") or []),
            "readiness_assessment": list(commands.get("readiness_assessment") or []),
            "delivery_proof": list(commands.get("delivery_proof") or []),
            "proof_spec": list(commands.get("proof_spec") or []),
            "docket": list(commands.get("docket") or []),
            "manifest": list(commands.get("manifest") or []),
            "queue": list(commands.get("queue") or []),
            "runbook": list(commands.get("runbook") or []),
            "verifier": list(commands.get("verifier") or []),
        },
        "proof_packet_template": execution_spec.get("proof_packet_template", {}),
        "execution_spec": execution_spec,
        "do_not_count_toppled_until": _count_toppled_requirements(execution_spec),
        "learning_policy": (
            "Append d185 capability-created learning only through the d210 verifier, "
            "only with --append-capability, and only after one real proof packet passes."
        ),
        "guardrails": {
            "live_submit_performed_by_verification_queue": False,
            "email_send_performed_by_verification_queue": False,
            "telegram_send_performed_by_verification_queue": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_verification_queue": False,
            "marginal_cost_usd": 0,
        },
    }


def _delivery_status_contract() -> dict[str, str]:
    return {
        "lead": "one controlled real Life assessment lead through the activated d193 path",
        "recipient_email_delivery_status": "real sent, delivered, queued_and_sent, success, or ok=true status",
        "founder_alert_status": "real sent, delivered, queued_and_sent, success, or ok=true status",
        "page_acknowledgement": assessment_delivery_proof.REQUIRED_RESPONSE_ACK,
        "capability_ledger_learning": "non-empty learning appended by the d210 verifier after pass",
        "verifier_pass": "assessment_delivery_proof.py returns status=pass with --append-capability",
    }


def _queue_gate(status: str) -> dict[str, Any]:
    return {
        "ready_to_queue_real_lead": status == "ready",
        "ready_to_run_verifier": status == "ready",
        "ready_to_count_toppled": False,
        "reason": (
            "d193 merge and guarded activation evidence are present; queue one controlled real lead, then verify."
            if status == "ready"
            else "Hold until d193 merge evidence and guarded activation evidence are both present."
        ),
        "topple_count_policy": "Only a passing d210 verifier row with capability-ledger append can count this domino toppled.",
    }


def _operator_steps(status: str) -> list[str]:
    if status != "ready":
        return [
            "Hold. This verification queue is not executable until d193 merge evidence and guarded activation evidence are both present.",
            "Re-run this verification queue after d193 is merged and d182/d188 activation evidence is visible.",
            "Do not submit a lead, send email, send founder alerts, or append capability learning from this held artifact.",
        ]
    return [
        "Queue exactly one controlled real Life assessment lead through the activated assessment path.",
        "Capture recipient email delivery status, founder alert status, API response, and page acknowledgement.",
        "Write the real proof packet using the template in this verification-queue artifact.",
        "Run the verifier command with --append-capability.",
        "Count the domino toppled only if the verifier returns status=pass and appends d185 capability learning.",
    ]


def _count_toppled_requirements(execution_spec: dict[str, Any]) -> list[str]:
    requirements = list(execution_spec.get("do_not_count_toppled_until") or [])
    if "d220 verification queue status=ready" not in requirements:
        requirements.insert(0, "d220 verification queue status=ready")
    return requirements


def render_markdown(verification_queue: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof Verification Queue",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{verification_queue['spec_id']}`",
        f"- Source: `{verification_queue['source_spec_id']}` at `{verification_queue['source_timestamp']}`",
        f"- Opportunity: `{verification_queue['opportunity_id']}`",
        f"- Status: `{verification_queue['status']}`",
        f"- Missing: `{', '.join(verification_queue.get('missing') or []) or 'none'}`",
        f"- Next domino score: `{verification_queue['next_domino_score']}`",
        "",
        "## Verification Queue Authority",
    ]
    for key, value in sorted((verification_queue.get("verification_queue_authority") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Delivery Status Contract"])
    for key, value in (verification_queue.get("delivery_status_contract") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Queue Gate"])
    for key, value in (verification_queue.get("queue_gate") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Operator Steps"])
    for index, step in enumerate(verification_queue.get("operator_steps") or [], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Verifier Command", "", "```bash"])
    lines.append(" ".join(str(part) for part in verification_queue.get("commands", {}).get("verifier") or []))
    lines.extend(["```", "", "## Do Not Count Toppled Until"])
    for item in verification_queue.get("do_not_count_toppled_until") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Guardrails"])
    for key, value in sorted((verification_queue.get("guardrails") or {}).items()):
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
    parser.add_argument("--verification-queue-file", type=Path, default=DEFAULT_VERIFICATION_QUEUE_FILE)
    parser.add_argument("--markdown-file", type=Path, default=DEFAULT_MARKDOWN_FILE)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    verification_queue = build_verification_queue(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.verification_queue_file, verification_queue)
        write_markdown(args.markdown_file, verification_queue)

    if args.json:
        print(json.dumps(verification_queue, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof-verification-queue: {verification_queue['status']}")
    return 0 if verification_queue["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
