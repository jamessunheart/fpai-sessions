#!/usr/bin/env python3
"""Package the d213 assessment delivery proof path as a local manifest.

This is a reversible verifier/spec artifact. It composes the existing d211
queue, d212 runbook, and d210 verifier so server ops have one delivery-proof
packet to follow after d193 is merged and activation evidence exists. It does
not submit a lead, send email, call Telegram, deploy, read secrets, append
capability learning, push, merge, or spend money.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.allocation import capability_ledger
from tools.build_loop import activation_audit, assessment_delivery_proof, assessment_delivery_proof_runbook


SPEC_ID = "SPEC_d213_auto-spot-topple-assessment-funn"
SOURCE_SPEC_ID = "SPEC_d194_spec-d194-the-spot-topple-orches"
OPPORTUNITY_ID = assessment_delivery_proof_runbook.OPPORTUNITY_ID
NEXT_DOMINO_SCORE = 100.4
DEFAULT_MANIFEST_FILE = Path("/opt/fpai-build/assessment_delivery_proof_manifest.json")
DEFAULT_MARKDOWN_FILE = Path("/opt/fpai-build/assessment_delivery_proof_manifest.md")


def build_manifest(
    *,
    repo_root: Path,
    ops_ledger: Path,
    proof_log: Path,
    capability_ledger_path: Path,
    proof_file_placeholder: str = "<real-proof-packet.json>",
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or assessment_delivery_proof.utc_now()
    runbook = assessment_delivery_proof_runbook.build_runbook(
        repo_root=repo_root,
        ops_ledger=ops_ledger,
        proof_log=proof_log,
        capability_ledger_path=capability_ledger_path,
        proof_file_placeholder=proof_file_placeholder,
        now=stamp,
    )
    queue = runbook.get("queue") if isinstance(runbook.get("queue"), dict) else {}
    status = "ready" if runbook.get("status") == "ready" else "hold"
    missing = list(runbook.get("missing") or [])
    verifier_command = list(runbook.get("verifier_command") or [])
    activation = queue.get("d193", {}).get("activation", {}) if isinstance(queue.get("d193"), dict) else {}

    return {
        "schema": "assessment_delivery_proof_manifest.v1",
        "ts": stamp,
        "spec_id": SPEC_ID,
        "source_spec_id": SOURCE_SPEC_ID,
        "opportunity_id": OPPORTUNITY_ID,
        "next_domino_score": NEXT_DOMINO_SCORE,
        "status": status,
        "missing": missing,
        "activation_audit": {
            "uses_d182_d188_evidence": True,
            "d193_activation_ok": bool(activation.get("ok")),
            "unexplained_inert_count": activation.get("unexplained_inert_count", 0),
        },
        "execution_gate": {
            "may_run_real_lead": status == "ready",
            "must_not_run_before": [
                "d193 merge evidence exists",
                "d193 guarded activation evidence exists",
            ],
            "count_toppled_only_after": [
                "one controlled real Life assessment lead is submitted by an operator",
                "recipient email delivery status is captured",
                "founder alert status is captured",
                "page acknowledgement is captured",
                "assessment_delivery_proof.py returns status=pass",
                "d185 capability-created ledger row is appended by the verifier",
            ],
        },
        "commands": {
            "queue": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_queue.py",
                "--repo-root",
                str(repo_root),
                "--ops-ledger",
                str(ops_ledger),
                "--json",
            ],
            "runbook": [
                "python3",
                "tools/build_loop/assessment_delivery_proof_runbook.py",
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
            "verifier": verifier_command,
        },
        "proof_packet_template": runbook.get("proof_packet_template", {}),
        "runbook": runbook,
        "learning_policy": (
            "Append d185 capability-created learning only through the verifier, "
            "only with --append-capability, and only after real proof passes."
        ),
        "guardrails": {
            "live_submit_performed_by_manifest": False,
            "email_send_performed_by_manifest": False,
            "telegram_send_performed_by_manifest": False,
            "secret_access_performed": False,
            "live_release_authority": False,
            "capability_append_performed_by_manifest": False,
            "marginal_cost_usd": 0,
        },
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Assessment Funnel Delivery Proof Manifest",
        "",
        "build_kind=library",
        "",
        f"- Spec: `{manifest['spec_id']}`",
        f"- Source: `{manifest['source_spec_id']}`",
        f"- Opportunity: `{manifest['opportunity_id']}`",
        f"- Status: `{manifest['status']}`",
        f"- Missing: `{', '.join(manifest.get('missing') or []) or 'none'}`",
        f"- Next domino score: `{manifest['next_domino_score']}`",
        "",
        "## Execution Gate",
    ]
    gate = manifest.get("execution_gate") or {}
    lines.append(f"- `may_run_real_lead`: `{gate.get('may_run_real_lead')}`")
    for item in gate.get("must_not_run_before") or []:
        lines.append(f"- Must not run before: {item}")
    for item in gate.get("count_toppled_only_after") or []:
        lines.append(f"- Count toppled only after: {item}")
    lines.extend(["", "## Verifier Command", "", "```bash"])
    lines.append(" ".join(str(part) for part in manifest.get("commands", {}).get("verifier") or []))
    lines.extend(["```", "", "## Guardrails"])
    for key, value in sorted((manifest.get("guardrails") or {}).items()):
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
    parser.add_argument("--manifest-file", type=Path, default=DEFAULT_MANIFEST_FILE)
    parser.add_argument("--markdown-file", type=Path, default=DEFAULT_MARKDOWN_FILE)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    manifest = build_manifest(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        proof_log=args.proof_log,
        capability_ledger_path=args.capability_ledger,
        proof_file_placeholder=args.proof_file_placeholder,
    )
    if not args.no_write:
        write_json(args.manifest_file, manifest)
        write_markdown(args.markdown_file, manifest)

    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"assessment-delivery-proof-manifest: {manifest['status']}")
    return 0 if manifest["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
