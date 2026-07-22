#!/usr/bin/env python3
"""Write the d226 assessment funnel delivery-proof verifier/spec.

This reversible local verifier/spec composes the d225 verification queue and the
d210-d225 verifier chain. It never submits leads, sends email, calls Telegram,
deploys, reads secrets, appends capability learning, pushes, merges, or spends
money.
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
from tools.build_loop import (
    activation_audit,
    assessment_delivery_proof,
    assessment_delivery_proof_delivery_proof_verification_queue,
)


SPEC_ID = "SPEC_d226_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
SOURCE_DECISION = "d226"
SOURCE_TIMESTAMP = "2026-07-22T16:12:28Z"
OPPORTUNITY_ID = assessment_delivery_proof_delivery_proof_verification_queue.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 99.76
UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE = 34
DEFAULT_DELIVERY_PROOF_FILE = Path("/opt/fpai-build/assessment_funnel_delivery_proof_delivery_proof.json")
DEFAULT_MARKDOWN_FILE = Path("/opt/fpai-build/assessment_funnel_delivery_proof_delivery_proof.md")


def build_delivery_proof_spec(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<real-proof-packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    verification_queue = assessment_delivery_proof_delivery_proof_verification_queue.build_verification_queue(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    status = "ready" if verification_queue.get("status") == "ready" else "hold"
    commands = verification_queue.get("commands") if isinstance(verification_queue.get("commands"), dict) else {}
    activation_gate = (
        verification_queue.get("activation_gate")
        if isinstance(verification_queue.get("activation_gate"), dict)
        else {}
    )

    return {
        "schema": "assessment_funnel_delivery_proof_delivery_proof.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_decision": SOURCE_DECISION,
        "source_spec_id": SOURCE_SPEC_ID,
        "source_timestamp": SOURCE_TIMESTAMP,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "activation_audit_unexplained_inert_count_before_queue": UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE,
        "status": status,
        "missing": list(verification_queue.get("missing") or []),
        "delivery_proof_authority": {
            "local_verifier_spec_only": True,
            "requires_d193_merged": True,
            "requires_d182_d188_activation_evidence": True,
            "operator_may_submit_one_controlled_life_lead_after_ready": status == "ready",
            "operator_may_run_verifier_after_real_proof_packet": status == "ready",
            "requires_real_recipient_delivery_status": True,
            "requires_real_founder_alert_status": True,
            "requires_page_acknowledgement": True,
            "requires_capability_ledger_learning": True,
            "sandbox_proof_counts": False,
            "delivery_proof_spec_counts_as_topple": False,
        },
        "activation_gate": {
            "d193_activation_ok": bool(activation_gate.get("d193_activation_ok")),
            "uses_d182_d188_evidence": bool(activation_gate.get("uses_d182_d188_evidence")),
            "unexplained_inert_count": activation_gate.get("unexplained_inert_count", 0),
        },
        "proof_contract": _proof_contract(),
        "execution_gate": _execution_gate(status),
        "operator_steps": _operator_steps(status),
        "commands": {
            "d226_delivery_proof_spec": [
                "python3",
                "tools/build_loop/assessment_funnel_delivery_proof_delivery_proof.py",
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
            "d225_verification_queue": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_delivery_proof_verification_queue.py",
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
            "verification_spec": list(commands.get("verification_spec") or []),
            "delivery_proof_queue": list(commands.get("delivery_proof_queue") or []),
            "delivery_proof_verifier": list(commands.get("delivery_proof_verifier") or []),
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
        "proof_packet_template": verification_queue.get("proof_packet_template", {}),
        "verification_queue": verification_queue,
        "do_not_count_toppled_until": _count_toppled_requirements(verification_queue),
        "learning_policy": (
            "Append the d185 capability-created ledger outcome only through the d210 verifier, "
            "only with --append-capability, and only after one real proof packet passes."
        ),
        "guardrails": {
            "live_submit_performed_by_delivery_proof_spec": False,
            "email_send_performed_by_delivery_proof_spec": False,
            "telegram_send_performed_by_delivery_proof_spec": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_delivery_proof_spec": False,
            "marginal_cost_usd": 0,
        },
    }


def _proof_contract() -> dict[str, str]:
    return {
        "lead": "one controlled real Life assessment lead through the activated d193 path",
        "recipient_email_delivery_status": "real sent, delivered, queued_and_sent, success, or ok=true status",
        "founder_alert_status": "real sent, delivered, queued_and_sent, success, or ok=true status",
        "page_acknowledgement": assessment_delivery_proof.REQUIRED_RESPONSE_ACK,
        "capability_ledger_learning": "non-empty learning appended by the d210 verifier after pass",
        "verifier_pass": "assessment_delivery_proof.py returns status=pass with --append-capability",
    }


def _execution_gate(status: str) -> dict[str, Any]:
    return {
        "ready_to_submit_controlled_life_lead": status == "ready",
        "ready_to_run_verifier": status == "ready",
        "ready_to_count_toppled": False,
        "reason": (
            "d193 merge and guarded activation evidence are present; submit one controlled Life lead, capture proof, then verify."
            if status == "ready"
            else "Hold until d193 merge evidence and guarded activation evidence are both present."
        ),
        "topple_count_policy": "Only a passing d210 verifier row with capability-ledger append can count this domino toppled.",
    }


def _operator_steps(status: str) -> list[str]:
    if status != "ready":
        return [
            "Hold. This delivery-proof spec is not executable until d193 merge evidence and guarded activation evidence are both present.",
            "Re-run this delivery-proof spec after d193 is merged and d182/d188 activation evidence is visible.",
            "Do not submit a lead, send email, send founder alerts, or append capability learning from this held artifact.",
        ]
    return [
        "Run or re-check the d225 verification queue and confirm status=ready.",
        "Submit exactly one controlled real Life assessment lead through the activated assessment path.",
        "Capture recipient email delivery status, founder alert status, API response, and page acknowledgement.",
        "Write the real proof packet using the template in this delivery-proof artifact.",
        "Run the verifier command with --append-capability.",
        "Count the domino toppled only if the verifier returns status=pass and appends d185 capability learning.",
    ]


def _count_toppled_requirements(verification_queue: dict[str, Any]) -> list[str]:
    requirements = list(verification_queue.get("do_not_count_toppled_until") or [])
    if "d226 delivery-proof spec status=ready" not in requirements:
        requirements.insert(0, "d226 delivery-proof spec status=ready")
    return requirements


def render_markdown(delivery_proof_spec: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{delivery_proof_spec['spec_id']}`",
        f"- Source: `{delivery_proof_spec['source_spec_id']}` at `{delivery_proof_spec['source_timestamp']}`",
        f"- Opportunity: `{delivery_proof_spec['opportunity_id']}`",
        f"- Status: `{delivery_proof_spec['status']}`",
        f"- Missing: `{', '.join(delivery_proof_spec.get('missing') or []) or 'none'}`",
        f"- Next domino score: `{delivery_proof_spec['next_domino_score']}`",
        "",
        "## Delivery Proof Authority",
    ]
    for key, value in sorted((delivery_proof_spec.get("delivery_proof_authority") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Proof Contract"])
    for key, value in (delivery_proof_spec.get("proof_contract") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Execution Gate"])
    for key, value in (delivery_proof_spec.get("execution_gate") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Operator Steps"])
    for index, step in enumerate(delivery_proof_spec.get("operator_steps") or [], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Verifier Command", "", "```bash"])
    lines.append(" ".join(str(part) for part in delivery_proof_spec.get("commands", {}).get("verifier") or []))
    lines.extend(["```", "", "## Do Not Count Toppled Until"])
    for item in delivery_proof_spec.get("do_not_count_toppled_until") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Guardrails"])
    for key, value in sorted((delivery_proof_spec.get("guardrails") or {}).items()):
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
    parser.add_argument("--delivery-proof-file", type=Path, default=DEFAULT_DELIVERY_PROOF_FILE)
    parser.add_argument("--markdown-file", type=Path, default=DEFAULT_MARKDOWN_FILE)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    delivery_proof_spec = build_delivery_proof_spec(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.delivery_proof_file, delivery_proof_spec)
        write_markdown(args.markdown_file, delivery_proof_spec)

    if args.json:
        print(json.dumps(delivery_proof_spec, indent=2, sort_keys=True))
    else:
        print(f"assessment-funnel-delivery-proof: {delivery_proof_spec['status']}")
    return 0 if delivery_proof_spec["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
