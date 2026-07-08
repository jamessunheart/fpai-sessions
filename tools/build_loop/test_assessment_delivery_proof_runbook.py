#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_loop import assessment_delivery_proof_runbook as runbook


class AssessmentDeliveryProofRunbookTests(unittest.TestCase):
    def make_root(self, root: Path, *, d193_status: str = "merged") -> None:
        (root / "core" / "BUILD").mkdir(parents=True)
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "schema": "build-registry.v1",
                    "active_builds": [
                        {
                            "id": runbook.assessment_delivery_proof_queue.D193_SPEC_IDS[0],
                            "branch": f"build/{runbook.assessment_delivery_proof_queue.D193_SPEC_IDS[0]}",
                            "status": d193_status,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def write_ops(self, path: Path, *, merged: bool = True, activated: bool = True) -> None:
        rows = []
        spec_id = runbook.assessment_delivery_proof_queue.D193_SPEC_IDS[0]
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

    def test_holds_when_queue_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root, d193_status="done")
            ops = root / "ops.jsonl"
            self.write_ops(ops, merged=False, activated=True)

            packet = runbook.build_runbook(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                now="2026-07-08T16:20:00Z",
            )

            self.assertEqual(packet["status"], "hold")
            self.assertFalse(packet["live_proof_authorized"])
            self.assertIn("d193_merged", packet["missing"])
            self.assertEqual(packet["queue"]["status"], "hold")
            self.assertIn("Do not run the live proof yet", packet["operator_steps"][0])
            self.assertFalse(packet["guardrails"]["live_submit_performed_by_runbook"])

    def test_ready_runbook_includes_verifier_and_proof_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)

            packet = runbook.build_runbook(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                proof_file_placeholder="/tmp/real-proof.json",
                now="2026-07-08T16:20:00Z",
            )

            self.assertEqual(packet["status"], "ready")
            self.assertTrue(packet["live_proof_authorized"])
            self.assertEqual(packet["missing"], [])
            self.assertEqual(packet["proof_packet_template"]["lens"], "life")
            self.assertIn("--append-capability", packet["verifier_command"])
            self.assertIn("/tmp/real-proof.json", packet["verifier_command"])
            self.assertIn("d185 capability-created learning", " ".join(packet["do_not_count_toppled_until"]))

    def test_cli_writes_json_and_markdown_runbook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            ops = root / "ops.jsonl"
            self.write_ops(ops)
            out = root / "runbook.json"
            md = root / "runbook.md"

            with redirect_stdout(StringIO()):
                rc = runbook.main(
                    [
                        "--repo-root",
                        str(root),
                        "--ops-ledger",
                        str(ops),
                        "--proof-log",
                        str(root / "proof.jsonl"),
                        "--capability-ledger",
                        str(root / "capability.jsonl"),
                        "--runbook-file",
                        str(out),
                        "--markdown-file",
                        str(md),
                        "--json",
                    ]
                )

            self.assertEqual(rc, 0)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], "assessment_delivery_proof_runbook.v1")
            self.assertEqual(saved["status"], "ready")
            text = md.read_text(encoding="utf-8")
            self.assertIn("Assessment Delivery Proof Runbook", text)
            self.assertIn("assessment_delivery_proof.py", text)


if __name__ == "__main__":
    unittest.main()
