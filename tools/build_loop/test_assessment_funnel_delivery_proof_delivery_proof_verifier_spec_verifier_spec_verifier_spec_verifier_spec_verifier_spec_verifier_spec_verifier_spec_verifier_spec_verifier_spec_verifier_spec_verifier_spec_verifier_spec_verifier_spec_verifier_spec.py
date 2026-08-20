#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_loop import assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec as verifier_spec

ROOT = Path(__file__).resolve().parents[2]


def d193_spec_id() -> str:
    return verifier_spec.assessment_delivery_proof.D193_SPEC_IDS[0]


class AssessmentFunnelDeliveryProofDeliveryProofVerifierSpecVerifierSpecVerifierSpecVerifierSpecVerifierSpecVerifierSpecTests(unittest.TestCase):
    def make_root(self, root: Path, *, d193_status: str = "merged") -> None:
        spec_id = d193_spec_id()
        (root / "core" / "BUILD").mkdir(parents=True)
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "schema": "build-registry.v1",
                    "active_builds": [
                        {
                            "id": spec_id,
                            "branch": f"build/{spec_id}",
                            "status": d193_status,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def write_ops(self, path: Path, *, merged: bool = True, activated: bool = True) -> None:
        spec_id = d193_spec_id()
        rows = []
        if merged:
            rows.append({"event": "merged", "artifact": spec_id, "detail": "d193 merged"})
        if activated:
            rows.append(
                {
                    "event": "activated",
                    "artifact": spec_id,
                    "detail": "d193 guarded activate smoke passed: champion-sign.service healthy",
                }
            )
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def test_holds_until_d193_merge_and_activation_evidence_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root, d193_status="done")
            ops = root / "ops.jsonl"
            self.write_ops(ops, merged=False, activated=True)

            packet = verifier_spec.build_verifier_spec(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                now="2026-08-06T16:20:01Z",
            )

            self.assertEqual(packet["schema"], f"{verifier_spec.ARTIFACT_STEM}.v1")
            self.assertEqual(packet["status"], "hold")
            self.assertTrue(packet["verifier_spec_authority"]["requires_d193_merged"])
            self.assertTrue(packet["verifier_spec_authority"]["requires_d182_d188_activation_evidence"])
            self.assertFalse(packet["verifier_spec_authority"]["operator_may_submit_one_controlled_life_lead_after_ready"])
            self.assertFalse(packet["verifier_spec_authority"]["verifier_spec_counts_as_topple"])
            self.assertIn("d193_merged", packet["missing"])
            self.assertIn("Hold.", packet["operator_steps"][0])
            self.assertFalse(packet["guardrails"]["email_send_performed_by_verifier_spec"])

    def test_ready_verifier_spec_wraps_d240_verifier_spec_with_d241_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)

            packet = verifier_spec.build_verifier_spec(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                proof_file_placeholder="/tmp/real-proof.json",
                now="2026-08-06T16:20:01Z",
            )

            self.assertEqual(packet["status"], "ready")
            self.assertEqual(packet["source_decision"], "d241")
            self.assertEqual(packet["source_timestamp"], "2026-08-06T16:20:01Z")
            self.assertEqual(packet["next_domino_score"], 121.07)
            self.assertEqual(packet["activation_audit_unexplained_inert_count_before_queue"], 34)
            self.assertTrue(packet["verifier_spec_authority"]["local_verifier_spec_only"])
            self.assertTrue(packet["verifier_spec_authority"]["operator_may_submit_one_controlled_life_lead_after_ready"])
            self.assertTrue(packet["verifier_spec_authority"]["operator_may_run_verifier_after_real_proof_packet"])
            self.assertFalse(packet["verifier_gate"]["ready_to_count_toppled"])
            self.assertEqual(packet["upstream_verifier_spec"]["status"], "ready")
            self.assertEqual(packet["upstream_verifier_spec"]["source_decision"], "d240")
            self.assertIn("recipient_email_delivery_status", packet["delivery_proof_contract"])
            self.assertIn("founder_alert_status", packet["delivery_proof_contract"])
            self.assertIn(
                "assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec.py",
                " ".join(packet["commands"]["d240_verifier_spec"]),
            )
            self.assertIn(
                "assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec.py",
                " ".join(packet["commands"]["d239_verifier_spec"]),
            )
            self.assertIn("assessment_delivery_proof.py", " ".join(packet["commands"]["verifier"]))
            self.assertIn("--append-capability", packet["commands"]["verifier"])
            self.assertIn("/tmp/real-proof.json", packet["commands"]["verifier"])
            self.assertIn("d241 verifier/spec status=ready", packet["do_not_count_toppled_until"])
            self.assertIn("d240 verifier/spec status=ready", packet["do_not_count_toppled_until"])
            self.assertIn("d239 verifier/spec status=ready", packet["do_not_count_toppled_until"])
            self.assertIn("d228 verifier/spec status=ready", packet["do_not_count_toppled_until"])

    def test_cli_writes_reversible_verifier_spec_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)
            out = root / "verifier-spec.json"
            md = root / "verifier-spec.md"

            with redirect_stdout(StringIO()):
                rc = verifier_spec.main(
                    [
                        "--repo-root",
                        str(root),
                        "--ops-ledger",
                        str(ops),
                        "--proof-log",
                        str(root / "proof.jsonl"),
                        "--capability-ledger",
                        str(root / "capability.jsonl"),
                        "--verifier-spec-file",
                        str(out),
                        "--markdown-file",
                        str(md),
                        "--json",
                    ]
                )

            self.assertEqual(rc, 0)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], f"{verifier_spec.ARTIFACT_STEM}.v1")
            self.assertEqual(saved["status"], "ready")
            text = md.read_text(encoding="utf-8")
            self.assertIn("Assessment Funnel Delivery Proof Delivery-Proof Verifier-Spec", text)
            self.assertIn("Verifier Spec Authority", text)
            self.assertIn("assessment_delivery_proof.py", text)

    def test_script_mode_cli_works_from_arbitrary_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "build_loop" / f"{verifier_spec.ARTIFACT_STEM}.py"),
                    "--repo-root",
                    str(root),
                    "--ops-ledger",
                    str(ops),
                    "--proof-log",
                    str(root / "proof.jsonl"),
                    "--capability-ledger",
                    str(root / "capability.jsonl"),
                    "--no-write",
                    "--json",
                ],
                cwd=root,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["schema"], f"{verifier_spec.ARTIFACT_STEM}.v1")


if __name__ == "__main__":
    unittest.main()
