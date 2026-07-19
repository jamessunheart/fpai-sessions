#!/usr/bin/env python3
"""Write the d223 delivery-proof queue/spec for assessment funnel proof.

This is a reversible local queue/spec artifact. It composes the d222
delivery-proof verifier/spec, which composes the d210-d221 verifier chain. It
does not submit leads, send email, call Telegram, deploy, read secrets, append
capability learning, push, merge, or spend money.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof, assessment_delivery_proof_delivery_proof_verifier


SPEC_ID = "SPEC_d223_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
SOURCE_DECISION = "d223"
SOURCE_TIMESTAMP = "2026-07-19T16:11:08Z"
OPPORTUNITY_ID = assessment_delivery_proof_delivery_proof_verifier.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 79.23
UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE = 34
DEFAULT_DELIVERY_PROOF_QUEUE_FILE = Path("/opt/fpai-build/assessment_delivery_proof_delivery_proof_queue.json")
DEFAULT_MARKDOWN_FILE = Path("/opt/fpai-build/assessment_delivery_proof_delivery_proof_queue.md")


def build_delivery_proof_queue(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<real-proof-packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    delivery_proof_verifier = assessment_delivery_proof_delivery_proof_verifier.build_delivery_proof_verifier(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    status = "ready" if delivery_proof_verifier.get("status") == "ready" else "hold"
    commands = delivery_proof_verifier.get("commands") if isinstance(delivery_proof_verifier.get("commands"), dict) else {}
    activation_gate = (
        delivery_proof_verifier.get("activation_gate")
        if isinstance(delivery_proof_verifier.get("activation_gate"), dict)
        else {}
    )

    return {
        "schema": "assessment_delivery_proof_delivery_proof_queue.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_decision": SOURCE_DECISION,
        "source_spec_id": SOURCE_SPEC_ID,
        "source_timestamp": SOURCE_TIMESTAMP,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "activation_audit_unexplained_inert_count_before_queue": UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE,
        "status": status,
        "missing": list(delivery_proof_verifier.get("missing") or []),
        "delivery_proof_queue_authority": {
            "local_queue_spec_only": True,
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
            "delivery_proof_queue_artifact_counts_as_topple": False,
        },
        "activation_gate": {
            "d193_activation_ok": bool(activation_gate.get("d193_activation_ok")),
            "uses_d182_d188_evidence": bool(activation_gate.get("uses_d182_d188_evidence")),
            "unexplained_inert_count": activation_gate.get("unexplained_inert_count", 0),
        },
        "delivery_proof_contract": _delivery_proof_contract(),
        "queue_gate": _queue_gate(status),
        "operator_steps": _operator_steps(status),
        "commands": {
            "delivery_proof_verifier": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_delivery_proof_verifier.py",
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
            "delivery_verifier": list(commands.get("delivery_verifier") or []),
            "verification_queue": list(commands.get("verification_queue") or []),
            "execution_spec": list(commands.get("execution_spec") or []),
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
        "proof_packet_template": delivery_proof_verifier.get("proof_packet_template", {}),
        "delivery_proof_verifier": delivery_proof_verifier,
        "do_not_count_toppled_until": _count_toppled_requirements(delivery_proof_verifier),
        "learning_policy": (
            "Append d185 capability-created learning only through the d210 verifier, "
            "only with --append-capability, and only after one real proof packet passes."
        ),
        "guardrails": {
            "live_submit_performed_by_delivery_proof_queue": False,
            "email_send_performed_by_delivery_proof_queue": False,
            "telegram_send_performed_by_delivery_proof_queue": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_delivery_proof_queue": False,
            "marginal_cost_usd": 0,
        },
    }


def _delivery_proof_contract() -> dict[str, str]:
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
            "Hold. This delivery-proof queue/spec is not executable until d193 merge evidence and guarded activation evidence are both present.",
            "Re-run this delivery-proof queue/spec after d193 is merged and d182/d188 activation evidence is visible.",
            "Do not submit a lead, send email, send founder alerts, or append capability learning from this held artifact.",
        ]
    return [
        "Run or re-check the d222 delivery-proof verifier/spec and confirm status=ready.",
        "Queue exactly one controlled real Life assessment lead through the activated assessment path.",
        "Capture recipient email delivery status, founder alert status, API response, and page acknowledgement.",
        "Write the real proof packet using the template in this delivery-proof queue/spec artifact.",
        "Run the verifier command with --append-capability.",
        "Count the domino toppled only if the verifier returns status=pass and appends d185 capability learning.",
    ]


def _count_toppled_requirements(delivery_proof_verifier: dict[str, Any]) -> list[str]:
    requirements = list(delivery_proof_verifier.get("do_not_count_toppled_until") or [])
    if "d223 delivery-proof queue/spec status=ready" not in requirements:
        requirements.insert(0, "d223 delivery-proof queue/spec status=ready")
    return requirements


def render_markdown(delivery_proof_queue: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof Queue",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{delivery_proof_queue['spec_id']}`",
        f"- Source: `{delivery_proof_queue['source_spec_id']}` at `{delivery_proof_queue['source_timestamp']}`",
        f"- Opportunity: `{delivery_proof_queue['opportunity_id']}`",
        f"- Status: `{delivery_proof_queue['status']}`",
        f"- Missing: `{', '.join(delivery_proof_queue.get('missing') or []) or 'none'}`",
        f"- Next domino score: `{delivery_proof_queue['next_domino_score']}`",
        "",
        "## Delivery Proof Queue Authority",
    ]
    for key, value in sorted((delivery_proof_queue.get("delivery_proof_queue_authority") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Delivery Proof Contract"])
    for key, value in (delivery_proof_queue.get("delivery_proof_contract") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Queue Gate"])
    for key, value in (delivery_proof_queue.get("queue_gate") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Operator Steps"])
    for index, step in enumerate(delivery_proof_queue.get("operator_steps") or [], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Verifier Command", "", "```bash"])
    lines.append(" ".join(str(part) for part in delivery_proof_queue.get("commands", {}).get("verifier") or []))
    lines.extend(["```", "", "## Do Not Count Toppled Until"])
    for item in delivery_proof_queue.get("do_not_count_toppled_until") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Guardrails"])
    for key, value in sorted((delivery_proof_queue.get("guardrails") or {}).items()):
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
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ops-ledger", type=Path, default=activation_audit.DEFAULT_OPS_LEDGER)
    parser.add_argument("--proof-log", type=Path, default=assessment_delivery_proof.DEFAULT_PROOF_LOG)
    parser.add_argument("--capability-ledger", type=Path, default=capability_ledger.DEFAULT_LEDGER)
    parser.add_argument("--proof-file-placeholder", default="<real-proof-packet.json>")
    parser.add_argument("--delivery-proof-queue-file", type=Path, default=DEFAULT_DELIVERY_PROOF_QUEUE_FILE)
    parser.add_argument("--markdown-file", type=Path, default=DEFAULT_MARKDOWN_FILE)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    delivery_proof_queue = build_delivery_proof_queue(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.delivery_proof_queue_file, delivery_proof_queue)
        write_markdown(args.markdown_file, delivery_proof_queue)

    if args.json:
        print(json.dumps(delivery_proof_queue, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof-delivery-proof-queue: {delivery_proof_queue['status']}")
    return 0 if delivery_proof_queue["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
