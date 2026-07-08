#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.allocation import capability_ledger
from tools.build_loop import assessment_delivery_proof as proof


def proof_packet() -> dict:
    return {
        "real_execution": True,
        "lens": "life",
        "lead_email": "proof@fullpotential.com",
        "response": {
            "ok": True,
            "filename": "2026-07-06-proof.md",
            "deliverable_status": "queued",
            "founder_alert": {"ok": True, "status": 200},
            "message": "Thank you, Proof. Your Allocation Score is on its way to your inbox.",
        },
        "recipient_email": {
            "status": "sent",
            "source": "journalctl",
            "detail": "assessment deliverable email sent lead=2026-07-06-proof.md",
        },
        "founder_alert": {"status": "sent", "detail": "Telegram founder alert returned 200"},
        "page_acknowledgement": {
            "status": "shown",
            "message": "Your Allocation Score is on its way to your inbox.",
        },
        "learning": "The Life assessment promise can complete end-to-end after d193 activation.",
    }


class AssessmentDeliveryProofTests(unittest.TestCase):
    def write_activation_evidence(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "event": "activated",
                    "artifact": "SPEC_d193_spec-d193-wire-the-assessment-fu",
                    "detail": "d193 guarded activate smoke passed: champion-sign.service healthy",
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def write_alternate_activation_evidence(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "event": "activated",
                    "artifact": "SPEC_d193_wire-assessment-funnel-auto-deliver",
                    "detail": "d193 guarded activate smoke passed: alternate spec id",
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_holds_without_d193_activation_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ops = root / "ops.jsonl"

            row = proof.build_result_row(
                repo_root=root,
                ops_ledger=ops,
                proof_packet=proof_packet(),
                proof_path=root / "proof.json",
                append_capability=False,
                capability_path=root / "capability.jsonl",
                now="2026-07-06T16:30:00Z",
            )

            self.assertEqual(row["status"], "hold")
            self.assertFalse(row["activation"]["ok"])
            self.assertTrue(row["proof"]["ok"])
            self.assertFalse((root / "capability.jsonl").exists())

    def test_holds_incomplete_proof_and_names_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ops = root / "ops.jsonl"
            self.write_activation_evidence(ops)
            packet = proof_packet()
            packet["recipient_email"] = {"status": "queued"}
            packet["page_acknowledgement"] = {"status": "shown", "message": "Thanks."}

            row = proof.build_result_row(
                repo_root=root,
                ops_ledger=ops,
                proof_packet=packet,
                proof_path=root / "proof.json",
                append_capability=True,
                capability_path=root / "capability.jsonl",
                now="2026-07-06T16:30:00Z",
            )

            self.assertEqual(row["status"], "hold")
            self.assertIn("recipient_email_sent", row["proof"]["missing"])
            self.assertIn("page_acknowledged", row["proof"]["missing"])
            self.assertFalse(row["capability_ledger_appended"])
            self.assertFalse((root / "capability.jsonl").exists())

    def test_pass_appends_capability_learning_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ops = root / "ops.jsonl"
            capability = root / "capability.jsonl"
            self.write_activation_evidence(ops)

            row = proof.build_result_row(
                repo_root=root,
                ops_ledger=ops,
                proof_packet=proof_packet(),
                proof_path=root / "proof.json",
                append_capability=True,
                capability_path=capability,
                now="2026-07-06T16:30:00Z",
            )

            self.assertEqual(row["status"], "pass")
            self.assertTrue(row["activation"]["ok"])
            self.assertTrue(row["proof"]["ok"])
            self.assertTrue(row["capability_ledger_appended"])
            rows = capability_ledger.read_rows(capability)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source_id"], proof.SPEC_ID)
            self.assertEqual(rows[0]["total_capability_gain"], 3.0)

    def test_pass_accepts_legacy_d193_activation_spec_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ops = root / "ops.jsonl"
            self.write_alternate_activation_evidence(ops)

            row = proof.build_result_row(
                repo_root=root,
                ops_ledger=ops,
                proof_packet=proof_packet(),
                proof_path=root / "proof.json",
                append_capability=False,
                capability_path=root / "capability.jsonl",
                now="2026-07-06T16:30:00Z",
            )

            self.assertEqual(row["status"], "pass")
            self.assertTrue(row["activation"]["ok"])

    def test_cli_writes_hold_log_for_sandbox_only_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ops = root / "ops.jsonl"
            self.write_activation_evidence(ops)
            packet = proof_packet()
            packet["sandbox_only"] = True
            proof_file = root / "proof.json"
            proof_file.write_text(json.dumps(packet), encoding="utf-8")
            proof_log = root / "proof-log.jsonl"

            with redirect_stdout(StringIO()):
                rc = proof.main([
                    "--repo-root", str(root),
                    "--ops-ledger", str(ops),
                    "--proof-file", str(proof_file),
                    "--proof-log", str(proof_log),
                    "--capability-ledger", str(root / "capability.jsonl"),
                    "--append-capability",
                    "--json",
                ])

            self.assertEqual(rc, 1)
            logged = json.loads(proof_log.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(logged["status"], "hold")
            self.assertIn("non_sandbox_proof", logged["proof"]["missing"])


if __name__ == "__main__":
    unittest.main()
