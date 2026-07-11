#!/usr/bin/env python3
"""Write the d215 local proof spec for assessment funnel delivery proof.

This is a reversible local verifier/spec. It composes the d214 proof docket,
which composes the d213 manifest, d212 runbook, d211 queue, and d210 verifier.
It does not submit leads, send email, call Telegram, deploy, read secrets,
append capability learning, push, merge, or spend money.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof, assessment_delivery_proof_docket


SPEC_ID = "SPEC_d215_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
SOURCE_DECISION = "d215"
SOURCE_TIMESTAMP = "2026-07-11T16:07:27Z"
OPPORTUNITY_ID = assessment_delivery_proof_docket.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 101.4
UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE = 34
DEFAULT_SPEC_FILE = Path("/opt/fpai-build/assessment_delivery_proof_spec.json")
DEFAULT_MARKDOWN_FILE = Path("/opt/fpai-build/assessment_delivery_proof_spec.md")


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
    docket = assessment_delivery_proof_docket.build_docket(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    status = "ready" if docket.get("status") == "ready" else "hold"
    commands = docket.get("commands") if isinstance(docket.get("commands"), dict) else {}
    activation = docket.get("activation_audit") if isinstance(docket.get("activation_audit"), dict) else {}

    return {
        "schema": "assessment_delivery_proof_spec.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_decision": SOURCE_DECISION,
        "source_spec_id": SOURCE_SPEC_ID,
        "source_timestamp": SOURCE_TIMESTAMP,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "activation_audit_unexplained_inert_count_before_queue": UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE,
        "status": status,
        "missing": list(docket.get("missing") or []),
        "execution_authority": {
            "local_spec_only": True,
            "operator_may_run_one_real_lead_after_ready": status == "ready",
            "requires_d193_merged": True,
            "requires_d182_d188_activation_evidence": True,
            "proof_must_be_real": True,
            "sandbox_proof_counts": False,
        },
        "activation_gate": {
            "d193_activation_ok": bool(activation.get("d193_activation_ok")),
            "uses_d182_d188_evidence": bool(activation.get("uses_d182_d188_evidence")),
            "unexplained_inert_count": activation.get("unexplained_inert_count", 0),
        },
        "proof_required": {
            "lead": "one controlled real Life assessment lead",
            "recipient_email_delivery_status": "required",
            "founder_alert_status": "required",
            "page_acknowledgement": assessment_delivery_proof.REQUIRED_RESPONSE_ACK,
            "capability_ledger_learning": "required; appended only by verifier after pass",
            "verifier_pass": "assessment_delivery_proof.py status=pass",
        },
        "operator_spec": _operator_spec(status),
        "commands": {
            "docket": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_docket.py",
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
            "manifest": list(commands.get("manifest") or []),
            "queue": list(commands.get("queue") or []),
            "runbook": list(commands.get("runbook") or []),
            "verifier": list(commands.get("verifier") or []),
        },
        "proof_packet_template": docket.get("proof_packet_template", {}),
        "docket": docket,
        "do_not_count_toppled_until": _count_toppled_requirements(docket),
        "learning_policy": (
            "Append d185 capability-created learning only through the d210 verifier, "
            "only with --append-capability, and only after one real proof packet passes."
        ),
        "guardrails": {
            "live_submit_performed_by_spec": False,
            "email_send_performed_by_spec": False,
            "telegram_send_performed_by_spec": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_spec": False,
            "marginal_cost_usd": 0,
        },
    }


def _operator_spec(status: str) -> list[str]:
    if status != "ready":
        return [
            "Hold. This proof spec is not executable until d193 merge evidence and guarded activation evidence are both present.",
            "Re-run this spec generator after d193 is merged and d182/d188 activation evidence is visible.",
            "Do not submit a lead, send email, send founder alerts, or append capability learning from this held spec.",
        ]
    return [
        "Submit exactly one controlled real Life assessment lead through the activated assessment path.",
        "Capture page acknowledgement, API response, recipient email delivery status, and founder alert status.",
        "Write the proof packet using the template in this spec.",
        "Run the verifier command with --append-capability.",
        "Count the domino toppled only if the verifier returns status=pass and appends d185 capability learning.",
    ]


def _count_toppled_requirements(docket: dict[str, Any]) -> list[str]:
    requirements = list(docket.get("do_not_count_toppled_until") or [])
    if "d215 local proof spec status=ready" not in requirements:
        requirements.insert(0, "d215 local proof spec status=ready")
    return requirements


def render_markdown(spec: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof Spec",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{spec['spec_id']}`",
        f"- Source: `{spec['source_spec_id']}` at `{spec['source_timestamp']}`",
        f"- Opportunity: `{spec['opportunity_id']}`",
        f"- Status: `{spec['status']}`",
        f"- Missing: `{', '.join(spec.get('missing') or []) or 'none'}`",
        f"- Next domino score: `{spec['next_domino_score']}`",
        "",
        "## Execution Authority",
    ]
    for key, value in sorted((spec.get("execution_authority") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Proof Required"])
    for key, value in (spec.get("proof_required") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Operator Spec"])
    for index, step in enumerate(spec.get("operator_spec") or [], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Verifier Command", "", "```bash"])
    lines.append(" ".join(str(part) for part in spec.get("commands", {}).get("verifier") or []))
    lines.extend(["```", "", "## Do Not Count Toppled Until"])
    for item in spec.get("do_not_count_toppled_until") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Guardrails"])
    for key, value in sorted((spec.get("guardrails") or {}).items()):
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
    parser.add_argument("--spec-file", type=Path, default=DEFAULT_SPEC_FILE)
    parser.add_argument("--markdown-file", type=Path, default=DEFAULT_MARKDOWN_FILE)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    spec = build_delivery_proof_spec(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.spec_file, spec)
        write_markdown(args.markdown_file, spec)

    if args.json:
        print(json.dumps(spec, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof-spec: {spec['status']}")
    return 0 if spec["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
