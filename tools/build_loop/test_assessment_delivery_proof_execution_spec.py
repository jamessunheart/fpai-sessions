#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_loop import assessment_delivery_proof_execution_spec as execution_spec


class AssessmentDeliveryProofExecutionSpecTests(unittest.TestCase):
    def make_root(self, root: Path, *, d193_status: str = "merged") -> None:
        spec_id = (
            execution_spec.assessment_delivery_proof_verifier_spec.assessment_delivery_proof_assessment
            .assessment_delivery_proof_delivery.assessment_delivery_proof_spec
            .assessment_delivery_proof_docket.assessment_delivery_proof_manifest
            .assessment_delivery_proof_runbook.assessment_delivery_proof_queue.D193_SPEC_IDS[0]
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
            execution_spec.assessment_delivery_proof_verifier_spec.assessment_delivery_proof_assessment
            .assessment_delivery_proof_delivery.assessment_delivery_proof_spec
            .assessment_delivery_proof_docket.assessment_delivery_proof_manifest
            .assessment_delivery_proof_runbook.assessment_delivery_proof_queue.D193_SPEC_IDS[0]
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

            packet = execution_spec.build_execution_spec(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                now="2026-07-15T16:09:14Z",
            )

            self.assertEqual(packet["schema"], "assessment_delivery_proof_execution_spec.v1")
            self.assertEqual(packet["status"], "hold")
            self.assertFalse(packet["execution_spec_authority"]["operator_may_run_one_real_lead_after_ready"])
            self.assertFalse(packet["execution_spec_authority"]["execution_spec_artifact_counts_as_topple"])
            self.assertIn("d193_merged", packet["missing"])
            self.assertIn("Hold.", packet["operator_steps"][0])
            self.assertFalse(packet["guardrails"]["email_send_performed_by_execution_spec"])

    def test_ready_execution_spec_wraps_d218_verifier_spec_with_d219_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)

            packet = execution_spec.build_execution_spec(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                proof_file_placeholder="/tmp/real-proof.json",
                now="2026-07-15T16:09:14Z",
            )

            self.assertEqual(packet["status"], "ready")
            self.assertEqual(packet["source_decision"], "d219")
            self.assertEqual(packet["source_timestamp"], "2026-07-15T16:09:14Z")
            self.assertEqual(packet["next_domino_score"], 87.4)
            self.assertEqual(packet["activation_audit_unexplained_inert_count_before_queue"], 34)
            self.assertTrue(packet["execution_spec_authority"]["local_execution_spec_only"])
            self.assertTrue(packet["execution_spec_authority"]["operator_may_run_one_real_lead_after_ready"])
            self.assertTrue(packet["execution_spec_authority"]["operator_may_run_verifier_after_real_proof_packet"])
            self.assertFalse(packet["execution_spec_authority"]["sandbox_proof_counts"])
            self.assertFalse(packet["execution_gate"]["ready_to_count_toppled"])
            self.assertEqual(packet["verifier_spec"]["status"], "ready")
            self.assertEqual(packet["verifier_spec"]["source_decision"], "d218")
            self.assertEqual(packet["delivery_proof_required"]["recipient_email_delivery_status"], "required in the real proof packet")
            self.assertEqual(packet["delivery_proof_required"]["founder_alert_status"], "required in the real proof packet")
            self.assertIn("assessment_delivery_proof_verifier_spec.py", " ".join(packet["commands"]["verifier_spec"]))
            self.assertIn("assessment_delivery_proof.py", " ".join(packet["commands"]["verifier"]))
            self.assertIn("--append-capability", packet["commands"]["verifier"])
            self.assertIn("/tmp/real-proof.json", packet["commands"]["verifier"])
            self.assertIn("d219 execution spec status=ready", packet["do_not_count_toppled_until"])
            self.assertIn("d218 verifier/spec status=ready", packet["do_not_count_toppled_until"])

    def test_cli_writes_reversible_execution_spec_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)
            out = root / "execution-spec.json"
            md = root / "execution-spec.md"

            with redirect_stdout(StringIO()):
                rc = execution_spec.main(
                    [
                        "--repo-root",
                        str(root),
                        "--ops-ledger",
                        str(ops),
                        "--proof-log",
                        str(root / "proof.jsonl"),
                        "--capability-ledger",
                        str(root / "capability.jsonl"),
                        "--execution-spec-file",
                        str(out),
                        "--markdown-file",
                        str(md),
                        "--json",
                    ]
                )

            self.assertEqual(rc, 0)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], "assessment_delivery_proof_execution_spec.v1")
            self.assertEqual(saved["status"], "ready")
            text = md.read_text(encoding="utf-8")
            self.assertIn("Assessment Funnel Delivery Proof Execution Spec", text)
            self.assertIn("Execution Spec Authority", text)
            self.assertIn("assessment_delivery_proof.py", text)


if __name__ == "__main__":
    unittest.main()
