#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_loop import assessment_delivery_proof_queue as queue


class AssessmentDeliveryProofQueueTests(unittest.TestCase):
    def make_root(self, root: Path, *, d193_status: str = "done") -> None:
        (root / "core" / "BUILD").mkdir(parents=True)
        (root / "core" / "BUILD" / "specs").mkdir(parents=True)
        (root / "core" / "BUILD" / "results").mkdir(parents=True)
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "schema": "build-registry.v1",
                    "active_builds": [
                        {
                            "id": queue.D193_SPEC_IDS[0],
                            "branch": f"build/{queue.D193_SPEC_IDS[0]}",
                            "status": d193_status,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def write_ops(self, path: Path, *, merged: bool = False, activated: bool = False) -> None:
        rows = []
        if merged:
            rows.append(
                {
                    "event": "merged",
                    "artifact": queue.D193_SPEC_IDS[0],
                    "detail": "d193 merged through reviewed build loop",
                }
            )
        if activated:
            rows.append(
                {
                    "event": "activated",
                    "artifact": queue.D193_SPEC_IDS[0],
                    "detail": "d193 guarded activate smoke passed: champion-sign.service healthy",
                }
            )
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def test_holds_until_d193_is_merged_and_activated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root, d193_status="done")
            ops = root / "ops.jsonl"
            self.write_ops(ops, activated=True)

            packet = queue.build_queue_packet(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                now="2026-07-07T16:30:00Z",
            )

            self.assertEqual(packet["status"], "hold")
            self.assertIn("d193_merged", packet["missing"])
            self.assertTrue(packet["d193"]["activation"]["ok"])
            self.assertFalse(packet["guardrails"]["email_send_performed_by_queue"])

    def test_ready_when_merge_and_activation_evidence_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root, d193_status="merged")
            ops = root / "ops.jsonl"
            self.write_ops(ops, merged=True, activated=True)

            packet = queue.build_queue_packet(
                repo_root=root,
                ops_ledger=ops,
                proof_log=root / "proof.jsonl",
                capability_ledger_path=root / "capability.jsonl",
                proof_file_placeholder="/tmp/proof-packet.json",
                now="2026-07-07T16:30:00Z",
            )

            self.assertEqual(packet["status"], "ready")
            self.assertEqual(packet["missing"], [])
            self.assertTrue(packet["d193"]["merged"]["ok"])
            self.assertTrue(packet["d193"]["activation"]["ok"])
            command = " ".join(packet["verifier"]["command"])
            self.assertIn("assessment_delivery_proof.py", command)
            self.assertIn("--append-capability", command)
            self.assertIn("/tmp/proof-packet.json", command)

    def test_cli_writes_reversible_queue_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root, d193_status="merged")
            ops = root / "ops.jsonl"
            out = root / "queue.json"
            self.write_ops(ops, merged=True, activated=True)

            with redirect_stdout(StringIO()):
                rc = queue.main(
                    [
                        "--repo-root",
                        str(root),
                        "--ops-ledger",
                        str(ops),
                        "--queue-file",
                        str(out),
                        "--proof-log",
                        str(root / "proof.jsonl"),
                        "--capability-ledger",
                        str(root / "capability.jsonl"),
                        "--json",
                    ]
                )

            self.assertEqual(rc, 0)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], "assessment_delivery_proof_queue.v1")
            self.assertEqual(saved["status"], "ready")
            self.assertFalse(saved["guardrails"]["live_submit_performed"])


if __name__ == "__main__":
    unittest.main()
