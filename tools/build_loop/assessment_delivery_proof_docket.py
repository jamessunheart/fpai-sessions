#!/usr/bin/env python3
"""Write the d214 local docket for assessment funnel delivery proof.

This is a reversible verifier/spec artifact. It composes the d213 manifest,
which composes the d212 runbook, d211 queue, and d210 verifier. The docket is
an operator-facing proof packet index; it does not submit leads, send email,
call Telegram, deploy, read secrets, append capability learning, push, merge,
or spend money.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof, assessment_delivery_proof_manifest


SPEC_ID = "SPEC_d214_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
SOURCE_DECISION = "d214"
SOURCE_TIMESTAMP = "2026-07-10T16:06:51Z"
OPPORTUNITY_ID = assessment_delivery_proof_manifest.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 101.4
UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE = 34
DEFAULT_DOCKET_FILE = Path("/opt/fpai-build/assessment_delivery_proof_docket.json")
DEFAULT_MARKDOWN_FILE = Path("/opt/fpai-build/assessment_delivery_proof_docket.md")


def build_docket(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<real-proof-packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    manifest = assessment_delivery_proof_manifest.build_manifest(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    status = "ready" if manifest.get("status") == "ready" else "hold"
    execution_gate = manifest.get("execution_gate") if isinstance(manifest.get("execution_gate"), dict) else {}
    activation_audit_summary = (
        manifest.get("activation_audit") if isinstance(manifest.get("activation_audit"), dict) else {}
    )
    commands = manifest.get("commands") if isinstance(manifest.get("commands"), dict) else {}
    missing = list(manifest.get("missing") or [])

    return {
        "schema": "assessment_delivery_proof_docket.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_decision": SOURCE_DECISION,
        "source_spec_id": SOURCE_SPEC_ID,
        "source_timestamp": SOURCE_TIMESTAMP,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "activation_audit_unexplained_inert_count_before_queue": UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE,
        "status": status,
        "missing": missing,
        "ready_to_collect_real_proof": status == "ready",
        "activation_audit": {
            "uses_d182_d188_evidence": True,
            "d193_activation_ok": bool(activation_audit_summary.get("d193_activation_ok")),
            "unexplained_inert_count": activation_audit_summary.get("unexplained_inert_count", 0),
        },
        "proof_docket": {
            "lead_scope": "one controlled real Life assessment lead after d193 merge and activation",
            "recipient_email_delivery_status": "required",
            "founder_alert_status": "required",
            "page_acknowledgement": assessment_delivery_proof.REQUIRED_RESPONSE_ACK,
            "capability_ledger_learning": "required; appended only by verifier after pass",
            "real_execution_required": True,
            "sandbox_only_allowed": False,
        },
        "operator_sequence": _operator_sequence(status),
        "commands": {
            "manifest": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_manifest.py",
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
            "queue": list(commands.get("queue") or []),
            "runbook": list(commands.get("runbook") or []),
            "verifier": list(commands.get("verifier") or []),
        },
        "proof_packet_template": manifest.get("proof_packet_template", {}),
        "manifest": manifest,
        "do_not_count_toppled_until": list(execution_gate.get("count_toppled_only_after") or []),
        "learning_policy": (
            "Append d185 capability-created learning only through the d210 verifier, "
            "only with --append-capability, and only after a real proof packet passes."
        ),
        "guardrails": {
            "live_submit_performed_by_docket": False,
            "email_send_performed_by_docket": False,
            "telegram_send_performed_by_docket": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_docket": False,
            "marginal_cost_usd": 0,
        },
    }


def _operator_sequence(status: str) -> list[str]:
    if status != "ready":
        return [
            "Hold. Do not run the controlled real lead until d193 merge evidence and guarded activation evidence are both present.",
            "Re-run this docket after d193 is merged and d182/d188 activation evidence is visible.",
        ]
    return [
        "Run one controlled real Life assessment lead on the activated /assessment path.",
        "Capture the API response, recipient email delivery evidence, founder alert evidence, and page acknowledgement.",
        "Write the real proof packet using the docket template.",
        "Run the verifier command with --append-capability.",
        "Count the domino toppled only after verifier status=pass and d185 capability learning is appended.",
    ]


def render_markdown(docket: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof Docket",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{docket['spec_id']}`",
        f"- Source: `{docket['source_spec_id']}` at `{docket['source_timestamp']}`",
        f"- Opportunity: `{docket['opportunity_id']}`",
        f"- Status: `{docket['status']}`",
        f"- Missing: `{', '.join(docket.get('missing') or []) or 'none'}`",
        f"- Next domino score: `{docket['next_domino_score']}`",
        "",
        "## Proof Docket",
    ]
    proof_docket = docket.get("proof_docket") if isinstance(docket.get("proof_docket"), dict) else {}
    for key, value in proof_docket.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Operator Sequence"])
    for index, step in enumerate(docket.get("operator_sequence") or [], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Verifier Command", "", "```bash"])
    lines.append(" ".join(str(part) for part in docket.get("commands", {}).get("verifier") or []))
    lines.extend(["```", "", "## Do Not Count Toppled Until"])
    for item in docket.get("do_not_count_toppled_until") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Guardrails"])
    for key, value in sorted((docket.get("guardrails") or {}).items()):
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
    parser.add_argument("--docket-file", type=Path, default=DEFAULT_DOCKET_FILE)
    parser.add_argument("--markdown-file", type=Path, default=DEFAULT_MARKDOWN_FILE)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    docket = build_docket(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.docket_file, docket)
        write_markdown(args.markdown_file, docket)

    if args.json:
        print(json.dumps(docket, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof-docket: {docket['status']}")
    return 0 if docket["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
