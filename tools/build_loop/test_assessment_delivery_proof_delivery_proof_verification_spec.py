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

from tools.build_loop import assessment_delivery_proof_delivery_proof_verification_spec as verification_spec

ROOT = Path(__file__).resolve().parents[2]


class AssessmentDeliveryProofDeliveryProofVerificationSpecTests(unittest.TestCase):
    def make_root(self, root: Path, *, d193_status: str = "merged") -> None:
        spec_id = (
            verification_spec.assessment_delivery_proof_delivery_proof_queue
            .assessment_delivery_proof_delivery_proof_verifier.assessment_delivery_proof_delivery_verifier
            .assessment_delivery_proof_verification_queue.assessment_delivery_proof_execution_spec
            .assessment_delivery_proof_verifier_spec.assessment_delivery_proof_assessment
            .assessment_delivery_proof_delivery.assessment_delivery_proof_spec
            .assessment_delivery_proof_docket.assessment_delivery_proof_manifest.assessment_delivery_proof_runbook
            .assessment_delivery_proof_queue.D193_SPEC_IDS[0]
        )
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
        spec_id = (
            verification_spec.assessment_delivery_proof_delivery_proof_queue
            .assessment_delivery_proof_delivery_proof_verifier.assessment_delivery_proof_delivery_verifier
            .assessment_delivery_proof_verification_queue.assessment_delivery_proof_execution_spec
            .assessment_delivery_proof_verifier_spec.assessment_delivery_proof_assessment
            .assessment_delivery_proof_delivery.assessment_delivery_proof_spec
            .assessment_delivery_proof_docket.assessment_delivery_proof_manifest.assessment_delivery_proof_runbook
            .assessment_delivery_proof_queue.D193_SPEC_IDS[0]
        )
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

            packet = verification_spec.build_verification_spec(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                now="2026-07-20T16:11:38Z",
            )

            self.assertEqual(packet["schema"], "assessment_delivery_proof_delivery_proof_verification_spec.v1")
            self.assertEqual(packet["status"], "hold")
            self.assertFalse(packet["verification_spec_authority"]["queued_for_real_execution_after_ready"])
            self.assertFalse(packet["verification_spec_authority"]["verification_spec_artifact_counts_as_topple"])
            self.assertIn("d193_merged", packet["missing"])
            self.assertIn("Hold.", packet["operator_steps"][0])
            self.assertFalse(packet["guardrails"]["email_send_performed_by_verification_spec"])

    def test_ready_verification_spec_wraps_d223_queue_with_d224_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)

            packet = verification_spec.build_verification_spec(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                proof_file_placeholder="/tmp/real-proof.json",
                now="2026-07-20T16:11:38Z",
            )

            self.assertEqual(packet["status"], "ready")
            self.assertEqual(packet["source_decision"], "d224")
            self.assertEqual(packet["source_timestamp"], "2026-07-20T16:11:38Z")
            self.assertEqual(packet["next_domino_score"], 84.4)
            self.assertEqual(packet["activation_audit_unexplained_inert_count_before_queue"], 34)
            self.assertTrue(packet["verification_spec_authority"]["local_verifier_spec_only"])
            self.assertTrue(packet["verification_spec_authority"]["operator_may_submit_one_controlled_life_lead_after_ready"])
            self.assertTrue(packet["verification_spec_authority"]["operator_may_run_verifier_after_real_proof_packet"])
            self.assertFalse(packet["verification_gate"]["ready_to_count_toppled"])
            self.assertEqual(packet["delivery_proof_queue"]["status"], "ready")
            self.assertEqual(packet["delivery_proof_queue"]["source_decision"], "d223")
            self.assertIn("recipient_email_delivery_status", packet["delivery_proof_contract"])
            self.assertIn("founder_alert_status", packet["delivery_proof_contract"])
            self.assertIn("assessment_delivery_proof_delivery_proof_queue.py", " ".join(packet["commands"]["delivery_proof_queue"]))
            self.assertIn("assessment_delivery_proof.py", " ".join(packet["commands"]["verifier"]))
            self.assertIn("--append-capability", packet["commands"]["verifier"])
            self.assertIn("/tmp/real-proof.json", packet["commands"]["verifier"])
            self.assertIn("d224 verification spec status=ready", packet["do_not_count_toppled_until"])
            self.assertIn("d223 delivery-proof queue/spec status=ready", packet["do_not_count_toppled_until"])
            self.assertIn("d222 delivery-proof verifier/spec status=ready", packet["do_not_count_toppled_until"])

    def test_cli_writes_reversible_verification_spec_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)
            out = root / "verification-spec.json"
            md = root / "verification-spec.md"

            with redirect_stdout(StringIO()):
                rc = verification_spec.main(
                    [
                        "--repo-root",
                        str(root),
                        "--ops-ledger",
                        str(ops),
                        "--proof-log",
                        str(root / "proof.jsonl"),
                        "--capability-ledger",
                        str(root / "capability.jsonl"),
                        "--verification-spec-file",
                        str(out),
                        "--markdown-file",
                        str(md),
                        "--json",
                    ]
                )

            self.assertEqual(rc, 0)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], "assessment_delivery_proof_delivery_proof_verification_spec.v1")
            self.assertEqual(saved["status"], "ready")
            text = md.read_text(encoding="utf-8")
            self.assertIn("Assessment Funnel Delivery Proof Verification Spec", text)
            self.assertIn("Verification Spec Authority", text)
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
                    str(ROOT / "tools" / "build_loop" / "assessment_delivery_proof_delivery_proof_verification_spec.py"),
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
            self.assertEqual(json.loads(result.stdout)["schema"], "assessment_delivery_proof_delivery_proof_verification_spec.v1")


if __name__ == "__main__":
    unittest.main()
