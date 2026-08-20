#!/usr/bin/env python3
"""Write the d245 assessment funnel delivery-proof verifier/spec.

This reversible local verifier/spec composes the d244 verifier/spec artifact and
the d210-d244 verifier chain. It never submits leads, sends email, calls
Telegram, deploys, reads secrets, appends capability learning, pushes, merges,
or spends money.
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
from tools.build_loop import activation_audit, assessment_delivery_proof
from tools.build_loop import assessment_funnel_delivery_proof_d244_verifier_spec as upstream


SPEC_ID = "SPEC_d245_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
SOURCE_DECISION = "d245"
SOURCE_TIMESTAMP = "2026-08-10T16:21:58Z"
OPPORTUNITY_ID = upstream.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 103.9
UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE = 34
ARTIFACT_STEM = "assessment_funnel_delivery_proof_d245_verifier_spec"
DEFAULT_VERIFIER_SPEC_FILE = Path(f"/opt/fpai-build/{ARTIFACT_STEM}.json")
DEFAULT_MARKDOWN_FILE = Path(f"/opt/fpai-build/{ARTIFACT_STEM}.md")


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
    upstream_verifier_spec = upstream.build_verifier_spec(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    status = "ready" if upstream_verifier_spec.get("status") == "ready" else "hold"
    commands = (
        upstream_verifier_spec.get("commands")
        if isinstance(upstream_verifier_spec.get("commands"), dict)
        else {}
    )
    activation_gate = (
        upstream_verifier_spec.get("activation_gate")
        if isinstance(upstream_verifier_spec.get("activation_gate"), dict)
        else {}
    )

    downstream_commands = dict(commands)
    downstream_commands.update(
        {
            "d245_verifier_spec": [
                "python3",
                f"tools/build_loop/{Path(__file__).name}",
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
            "d244_verifier_spec": [
                "python3",
                "tools/build_loop/assessment_funnel_delivery_proof_d244_verifier_spec.py",
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
        }
    )

    return {
        "schema": f"{ARTIFACT_STEM}.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_decision": SOURCE_DECISION,
        "source_spec_id": SOURCE_SPEC_ID,
        "source_timestamp": SOURCE_TIMESTAMP,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "activation_audit_unexplained_inert_count_before_queue": UNEXPLAINED_INERT_COUNT_BEFORE_QUEUE,
        "status": status,
        "missing": list(upstream_verifier_spec.get("missing") or []),
        "verifier_spec_authority": {
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
            "verifier_spec_counts_as_topple": False,
        },
        "activation_gate": {
            "d193_activation_ok": bool(activation_gate.get("d193_activation_ok")),
            "uses_d182_d188_evidence": bool(activation_gate.get("uses_d182_d188_evidence")),
            "unexplained_inert_count": activation_gate.get("unexplained_inert_count", 0),
        },
        "delivery_proof_contract": upstream_verifier_spec.get("delivery_proof_contract", {}),
        "verifier_gate": _verifier_gate(status),
        "operator_steps": _operator_steps(status),
        "commands": downstream_commands,
        "proof_packet_template": upstream_verifier_spec.get("proof_packet_template", {}),
        "upstream_verifier_spec": upstream_verifier_spec,
        "do_not_count_toppled_until": _count_toppled_requirements(upstream_verifier_spec),
        "learning_policy": (
            "Append the d185 capability-created ledger outcome only through the d210 verifier, "
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


def _verifier_gate(status: str) -> dict[str, Any]:
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
            "Hold. This verifier/spec is not executable until d193 merge evidence and guarded activation evidence are both present.",
            "Re-run this verifier/spec after d193 is merged and d182/d188 activation evidence is visible.",
            "Do not submit a lead, send email, send founder alerts, or append capability learning from this held artifact.",
        ]
    return [
        "Run or re-check the d244 verifier/spec and confirm status=ready.",
        "Submit exactly one controlled real Life assessment lead through the activated assessment path.",
        "Capture recipient email delivery status, founder alert status, API response, and page acknowledgement.",
        "Write the real proof packet using the template in this verifier/spec artifact.",
        "Run the verifier command with --append-capability.",
        "Count the domino toppled only if the verifier returns status=pass and appends d185 capability learning.",
    ]


def _count_toppled_requirements(upstream_verifier_spec: dict[str, Any]) -> list[str]:
    requirements = list(upstream_verifier_spec.get("do_not_count_toppled_until") or [])
    if "d245 verifier/spec status=ready" not in requirements:
        requirements.insert(0, "d245 verifier/spec status=ready")
    return requirements


def render_markdown(verifier_spec: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof Delivery-Proof Verifier-Spec Verifier-Spec Verifier-Spec",
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
    lines.extend(["", "## Delivery Proof Contract"])
    for key, value in (verifier_spec.get("delivery_proof_contract") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Verifier Gate"])
    for key, value in (verifier_spec.get("verifier_gate") or {}).items():
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
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
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
        print(f"assessment-funnel-delivery-proof verifier/spec: {verifier_spec['status']}")
    return 0 if verifier_spec["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
