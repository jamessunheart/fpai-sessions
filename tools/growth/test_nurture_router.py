from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.growth import nurture_router as nr


class NurtureRouterTests(unittest.TestCase):
    def test_routes_weak_dimension_to_matching_sequence(self) -> None:
        lead = {
            "lead_id": "lead-1",
            "email": "owner@example.com",
            "name": "Owner",
            "company": "Acme",
            "utm_campaign": "assessment-savings",
            "scores": {"capital": 82, "time": 76, "attention": 61, "people": 70, "ai": 24, "knowledge": 52},
        }
        packet = nr.build_nurture_packet(lead)
        route = packet["route"]
        self.assertEqual(route["weakest_dimension"], "ai")
        self.assertEqual(route["route"], "partnership")
        self.assertEqual(route["listmonk_list"], "fpai-partnership-nurture")
        self.assertEqual(len(packet["n8n"]["steps"]), 5)
        self.assertEqual(len(packet["ledger_rows"]), 5)
        first = packet["ledger_rows"][0]
        self.assertEqual(first["type"], "email")
        self.assertEqual(first["parent_id"], "assessment-savings")
        self.assertEqual(first["genome"]["channel"], "email")
        self.assertIn("utm", json.dumps(packet).lower())

    def test_proxy_scores_route_from_plain_text_lead_and_append_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lead = root / "lead.txt"
            out = root / "packet.json"
            ledger = root / "nurture.jsonl"
            lead.write_text(
                "Name: Taylor\nEmail: taylor@example.com\nBottleneck: Manual spreadsheet handoffs waste hours every week\n",
                encoding="utf-8",
            )
            rc = nr.main(["--lead", str(lead), "--out", str(out), "--ledger-jsonl", str(ledger)])
            self.assertEqual(rc, 0)
            packet = json.loads(out.read_text(encoding="utf-8"))
            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(packet["route"]["weakest_dimension"], "time")
        self.assertEqual(packet["route"]["route"], "blueprint")
        self.assertEqual(len(rows), 5)


if __name__ == "__main__":
    unittest.main()
