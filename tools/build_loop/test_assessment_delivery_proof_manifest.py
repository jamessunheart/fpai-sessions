#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_loop import assessment_delivery_proof_manifest as manifest


class AssessmentDeliveryProofManifestTests(unittest.TestCase):
    def make_root(self, root: Path, *, d193_status: str = "merged") -> None:
        spec_id = manifest.assessment_delivery_proof_runbook.assessment_delivery_proof_queue.D193_SPEC_IDS[0]
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
        spec_id = manifest.assessment_delivery_proof_runbook.assessment_delivery_proof_queue.D193_SPEC_IDS[0]
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

            packet = manifest.build_manifest(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                now="2026-07-09T16:06:30Z",
            )

            self.assertEqual(packet["schema"], "assessment_delivery_proof_manifest.v1")
            self.assertEqual(packet["status"], "hold")
            self.assertFalse(packet["execution_gate"]["may_run_real_lead"])
            self.assertIn("d193_merged", packet["missing"])
            self.assertFalse(packet["guardrails"]["email_send_performed_by_manifest"])

    def test_ready_manifest_packages_runbook_queue_and_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)

            packet = manifest.build_manifest(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                proof_file_placeholder="/tmp/real-proof.json",
                now="2026-07-09T16:06:30Z",
            )

            self.assertEqual(packet["status"], "ready")
            self.assertTrue(packet["execution_gate"]["may_run_real_lead"])
            self.assertEqual(packet["missing"], [])
            self.assertEqual(packet["source_spec_id"], manifest.SOURCE_SPEC_ID)
            self.assertEqual(packet["next_domino_score"], 100.4)
            self.assertEqual(packet["runbook"]["status"], "ready")
            self.assertIn("assessment_delivery_proof_queue.py", " ".join(packet["commands"]["queue"]))
            self.assertIn("assessment_delivery_proof_runbook.py", " ".join(packet["commands"]["runbook"]))
            self.assertIn("assessment_delivery_proof.py", " ".join(packet["commands"]["verifier"]))
            self.assertIn("--append-capability", packet["commands"]["verifier"])
            self.assertIn("/tmp/real-proof.json", packet["commands"]["verifier"])
            self.assertIn("d185 capability-created ledger row", " ".join(packet["execution_gate"]["count_toppled_only_after"]))

    def test_cli_writes_reversible_manifest_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)
            out = root / "manifest.json"
            md = root / "manifest.md"

            with redirect_stdout(StringIO()):
                rc = manifest.main(
                    [
                        "--repo-root",
                        str(root),
                        "--ops-ledger",
                        str(ops),
                        "--proof-log",
                        str(root / "proof.jsonl"),
                        "--capability-ledger",
                        str(root / "capability.jsonl"),
                        "--manifest-file",
                        str(out),
                        "--markdown-file",
                        str(md),
                        "--json",
                    ]
                )

            self.assertEqual(rc, 0)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], "assessment_delivery_proof_manifest.v1")
            self.assertEqual(saved["status"], "ready")
            text = md.read_text(encoding="utf-8")
            self.assertIn("Assessment Funnel Delivery Proof Manifest", text)
            self.assertIn("Count toppled only after", text)


if __name__ == "__main__":
    unittest.main()
