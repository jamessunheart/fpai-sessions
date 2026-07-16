#!/usr/bin/env python3
"""Write the d218 verifier/spec for assessment funnel delivery proof.

This is a reversible local verifier/spec artifact. It composes the d217
readiness assessment, which composes the d216 delivery proof and the d210
verifier chain. It does not submit leads, send email, call Telegram, deploy,
read secrets, append capability learning, push, merge, or spend money.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof, assessment_delivery_proof_assessment


SPEC_ID = "SPEC_d218_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
SOURCE_DECISION = "d218"
SOURCE_TIMESTAMP = "2026-07-14T16:08:47Z"
OPPORTUNITY_ID = assessment_delivery_proof_assessment.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 85.4
UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE = 34
DEFAULT_VERIFIER_SPEC_FILE = Path("/opt/fpai-build/assessment_delivery_proof_verifier_spec.json")
DEFAULT_MARKDOWN_FILE = Path("/opt/fpai-build/assessment_delivery_proof_verifier_spec.md")


def build_verifier_spec(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<real-proof-packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    assessment = assessment_delivery_proof_assessment.build_delivery_proof_assessment(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    status = "ready" if assessment.get("status") == "ready" else "hold"
    activation_gate = (
        assessment.get("activation_gate") if isinstance(assessment.get("activation_gate"), dict) else {}
    )
    commands = assessment.get("commands") if isinstance(assessment.get("commands"), dict) else {}

    return {
        "schema": "assessment_delivery_proof_verifier_spec.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_decision": SOURCE_DECISION,
        "source_spec_id": SOURCE_SPEC_ID,
        "source_timestamp": SOURCE_TIMESTAMP,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "activation_audit_unexplained_inert_count_before_queue": UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE,
        "status": status,
        "missing": list(assessment.get("missing") or []),
        "verifier_spec_authority": {
            "local_verifier_spec_only": True,
            "operator_may_run_verifier_after_real_proof_packet": status == "ready",
            "requires_d193_merged": True,
            "requires_d182_d188_activation_evidence": True,
            "requires_one_real_life_assessment_lead": True,
            "proof_must_be_real": True,
            "sandbox_proof_counts": False,
            "verifier_spec_artifact_counts_as_topple": False,
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
            "readiness_assessment": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_assessment.py",
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
            "delivery_proof": list(commands.get("delivery_proof") or []),
            "proof_spec": list(commands.get("proof_spec") or []),
            "docket": list(commands.get("docket") or []),
            "manifest": list(commands.get("manifest") or []),
            "queue": list(commands.get("queue") or []),
            "runbook": list(commands.get("runbook") or []),
            "verifier": list(commands.get("verifier") or []),
        },
        "proof_packet_template": assessment.get("proof_packet_template", {}),
        "readiness_assessment": assessment,
        "do_not_count_toppled_until": _count_toppled_requirements(assessment),
        "learning_policy": (
            "Append d185 capability-created learning only through the d210 verifier, "
            "only with --append-capability, and only after one real proof packet passes."
        ),
        "guardrails": {
            "live_submit_performed_by_verifier_spec": False,
            "email_send_performed_by_verifier_spec": False,
            "telegram_send_performed_by_verifier_spec": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_verifier_spec": False,
            "marginal_cost_usd": 0,
        },
    }


def _proof_contract() -> dict[str, str]:
    return {
        "lead": "one controlled real Life assessment lead through the activated d193 path",
        "recipient_email_delivery_status": "required in the real proof packet",
        "founder_alert_status": "required in the real proof packet",
        "page_acknowledgement": assessment_delivery_proof.REQUIRED_RESPONSE_ACK,
        "capability_ledger_learning": "required; appended only by the d210 verifier after pass",
        "verifier_pass": "assessment_delivery_proof.py status=pass with --append-capability",
    }


def _execution_gate(status: str) -> dict[str, Any]:
    return {
        "ready_to_run_real_lead": status == "ready",
        "ready_to_run_verifier": status == "ready",
        "ready_to_count_toppled": False,
        "reason": (
            "d193 merge and guarded activation evidence are present; collect one real proof packet, then run verifier."
            if status == "ready"
            else "Hold until d193 merge evidence and guarded activation evidence are both present."
        ),
    }


def _operator_steps(status: str) -> list[str]:
    if status != "ready":
        return [
            "Hold. This verifier/spec is not executable until d193 merge evidence and guarded activation evidence are both present.",
            "Re-run this verifier/spec after d193 is merged and d182/d188 activation evidence is visible.",
            "Do not submit a lead, send email, send founder alerts, or append capability learning from this held artifact.",
        ]
    return [
        "Submit exactly one controlled real Life assessment lead through the activated assessment path.",
        "Capture page acknowledgement, API response, recipient email delivery status, and founder alert status.",
        "Write the real proof packet using the template in this verifier/spec artifact.",
        "Run the verifier command with --append-capability.",
        "Count the domino toppled only if the verifier returns status=pass and appends d185 capability learning.",
    ]


def _count_toppled_requirements(assessment: dict[str, Any]) -> list[str]:
    requirements = list(assessment.get("do_not_count_toppled_until") or [])
    if "d218 verifier/spec status=ready" not in requirements:
        requirements.insert(0, "d218 verifier/spec status=ready")
    return requirements


def render_markdown(verifier_spec: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof Verifier Spec",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{verifier_spec['spec_id']}`",
        f"- Source: `{verifier_spec['source_spec_id']}` at `{verifier_spec['source_timestamp']}`",
        f"- Opportunity: `{verifier_spec['opportunity_id']}`",
        f"- Status: `{verifier_spec['status']}`",
        f"- Missing: `{', '.join(verifier_spec.get('missing') or []) or 'none'}`",
        f"- Next domino score: `{verifier_spec['next_domino_score']}`",
        "",
        "## Verifier Spec Authority",
    ]
    for key, value in sorted((verifier_spec.get("verifier_spec_authority") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Proof Contract"])
    for key, value in (verifier_spec.get("proof_contract") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Execution Gate"])
    for key, value in (verifier_spec.get("execution_gate") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Operator Steps"])
    for index, step in enumerate(verifier_spec.get("operator_steps") or [], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Verifier Command", "", "```bash"])
    lines.append(" ".join(str(part) for part in verifier_spec.get("commands", {}).get("verifier") or []))
    lines.extend(["```", "", "## Do Not Count Toppled Until"])
    for item in verifier_spec.get("do_not_count_toppled_until") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Guardrails"])
    for key, value in sorted((verifier_spec.get("guardrails") or {}).items()):
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
    parser.add_argument("--verifier-spec-file", type=Path, default=DEFAULT_VERIFIER_SPEC_FILE)
    parser.add_argument("--markdown-file", type=Path, default=DEFAULT_MARKDOWN_FILE)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    verifier_spec = build_verifier_spec(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.verifier_spec_file, verifier_spec)
        write_markdown(args.markdown_file, verifier_spec)

    if args.json:
        print(json.dumps(verifier_spec, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof-verifier-spec: {verifier_spec['status']}")
    return 0 if verifier_spec["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
