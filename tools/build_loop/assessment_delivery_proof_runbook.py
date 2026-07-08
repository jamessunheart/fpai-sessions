#!/usr/bin/env python3
"""Write the local assessment delivery proof runbook after d193 is live.

This is a reversible planning/spec layer. It composes the d211 readiness queue
and the d210 verifier, but it does not submit leads, send email, call Telegram,
deploy, read secrets, append capability learning, push, merge, or spend money.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof, assessment_delivery_proof_queue


SPEC_ID = "SPEC_d212_auto-spot-topple-assessment-funn"
OPPORTUNITY_ID = assessment_delivery_proof_queue.OPPORTUNITY_ID
DEFAULT_RUNBOOK_FILE = Path("/opt/fpai-build/assessment_delivery_proof_runbook.json")


def build_runbook(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<real-proof-packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    queue_packet = assessment_delivery_proof_queue.build_queue_packet(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    ready = queue_packet.get("status") == "ready"
    verifier_command = list(queue_packet.get("verifier", {}).get("command") or [])
    ready_steps = [
        "Confirm d193 is merged and guarded activation evidence is logged through d182/d188.",
        "Submit exactly one controlled real Life assessment lead on the activated /assessment path.",
        "Collect the API response, recipient email delivery evidence, founder alert evidence, page acknowledgement, and one learning sentence.",
        "Save those facts as the proof packet named in the verifier command.",
        "Run the verifier command; count the domino toppled only if it returns status=pass and appends d185 capability learning.",
    ]
    hold_steps = [
        "Do not run the live proof yet; this runbook is on hold until all missing preconditions are cleared.",
        "Re-run the runbook after d193 merge and guarded activation evidence are visible in registry/ops-ledger evidence.",
    ]
    return {
        "schema": "assessment_delivery_proof_runbook.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "opportunity_id": OPPORTUNITY_ID,
        "status": "ready" if ready else "hold",
        "live_proof_authorized": ready,
        "missing": list(queue_packet.get("missing") or []),
        "queue": queue_packet,
        "operator_steps": ready_steps if ready else hold_steps,
        "proof_packet_template": {
            "real_execution": True,
            "lens": "life",
            "lead_email": "<controlled-test-lead-email>",
            "response": {
                "ok": True,
                "deliverable_status": "queued",
                "founder_alert": {"ok": True, "status": "<status-code-or-detail>"},
                "message": "Thank you. Your Allocation Score is on its way to your inbox.",
            },
            "recipient_email": {
                "status": "sent|delivered|success",
                "source": "<mail log, mailbox, or provider evidence>",
                "detail": "<delivery evidence>",
            },
            "founder_alert": {
                "status": "sent|delivered|success",
                "detail": "<Telegram/founder alert evidence>",
            },
            "page_acknowledgement": {
                "status": "shown",
                "message": assessment_delivery_proof.REQUIRED_RESPONSE_ACK,
            },
            "learning": "<capability learning from the real run>",
        },
        "verifier_command": verifier_command,
        "do_not_count_toppled_until": [
            "verifier status=pass",
            "recipient email delivery status is present",
            "founder alert status is present",
            "page acknowledgement is present",
            "d185 capability-created learning is appended by the verifier",
        ],
        "guardrails": {
            "live_submit_performed_by_runbook": False,
            "email_send_performed_by_runbook": False,
            "telegram_send_performed_by_runbook": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_runbook": False,
            "marginal_cost_usd": 0,
        },
    }


def render_markdown(runbook: dict[str, Any]) -> str:
    lines = [
        "# Assessment Delivery Proof Runbook",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{runbook['spec_id']}`",
        f"- Opportunity: `{runbook['opportunity_id']}`",
        f"- Status: `{runbook['status']}`",
        f"- Missing: `{', '.join(runbook.get('missing') or []) or 'none'}`",
        "",
        "## Operator Steps",
    ]
    for index, step in enumerate(runbook.get("operator_steps") or [], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(
        [
            "",
            "## Verifier Command",
            "",
            "```bash",
            " ".join(str(part) for part in runbook.get("verifier_command") or []),
            "```",
            "",
            "## Guardrails",
        ]
    )
    for key, value in sorted((runbook.get("guardrails") or {}).items()):
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
    parser.add_argument("--runbook-file", type=Path, default=DEFAULT_RUNBOOK_FILE)
    parser.add_argument("--markdown-file", type=Path)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    runbook = build_runbook(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.runbook_file, runbook)
        if args.markdown_file:
            write_markdown(args.markdown_file, runbook)

    if args.json:
        print(json.dumps(runbook, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof-runbook: {runbook['status']}")
    return 0 if runbook["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
