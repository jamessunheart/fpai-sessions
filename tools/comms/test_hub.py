from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.comms import hub
from tools.comms.channels.email import EmailReadNotConfigured, ingest_read_only
from tools.queue.build import load_queue


class CommsHubTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-comms-"))

    def fixture(self, root: Path) -> Path:
        path = root / "messages.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "id": "m1",
                        "from": "founder@example.com",
                        "subject": "Interested in the bottleneck session",
                        "body": "Can you send me details about the 90 minute session?",
                    },
                    {
                        "id": "m2",
                        "from": "ops@example.com",
                        "subject": "Weekly update",
                        "body": "Just sharing the update. No reply needed.",
                    },
                    {
                        "id": "m3",
                        "from": "assistant@example.com",
                        "subject": "Action needed: confirm schedule",
                        "body": "Please confirm the schedule by Friday.",
                    },
                    {
                        "id": "m4",
                        "from": "spam@example.com",
                        "subject": "Limited time offer",
                        "body": "Buy our SEO services. Unsubscribe here.",
                    },
                ]
            ),
            encoding="utf-8",
        )
        return path

    def test_fixture_ingest_and_triage_classes(self) -> None:
        messages = ingest_read_only(fixture=self.fixture(self.root()))

        results = hub.triage(messages)

        self.assertEqual([item["class"] for item in results], ["needs-reply", "fyi", "action", "spam"])
        self.assertIn("Draft a reply", results[0].suggested_next)

    def test_needs_reply_stages_draft_and_reserved_send_gate(self) -> None:
        root = self.root()
        lane = root / "COMMS_LANE.md"
        queue = root / "queue.json"

        run = hub.run_fixture(self.fixture(root), dry_run=False, lane_path=lane, queue_path=queue)

        self.assertEqual(len(run.triage), 4)
        self.assertEqual(len(run.drafts), 2)
        self.assertEqual(len(run.gates), 2)
        self.assertTrue(lane.exists())
        self.assertIn("Comms Lane", lane.read_text(encoding="utf-8"))
        self.assertIn("review", lane.read_text(encoding="utf-8").lower())
        gates = load_queue(queue)["gates"]
        self.assertEqual(gates[0]["id"], run.drafts[0].gate_id)
        self.assertEqual(gates[0]["verbs"], ["approve", "edit", "skip"])
        self.assertIn("Send draft to founder@example.com?", gates[0]["question"])
        self.assertEqual(run.drafts[0].reserved_verdict["category"], "public_outbound_send")

    def test_dry_run_writes_nothing(self) -> None:
        root = self.root()
        lane = root / "COMMS_LANE.md"
        queue = root / "queue.json"

        run = hub.run_fixture(self.fixture(root), dry_run=True, lane_path=lane, queue_path=queue)

        self.assertEqual(len(run.drafts), 2)
        self.assertEqual(run.gates, [])
        self.assertFalse(lane.exists())
        self.assertFalse(queue.exists())

    def test_email_live_read_has_no_implicit_send_or_live_adapter(self) -> None:
        self.assertEqual(ingest_read_only(), [])
        with mock.patch.dict("os.environ", {"FPAI_EMAIL_READ_TOKEN": "set"}):
            with self.assertRaises(EmailReadNotConfigured):
                ingest_read_only()

    def test_intake_agent_follow_up_is_reported_not_fixed(self) -> None:
        root = self.root()
        lane = root / "COMMS_LANE.md"

        hub.run_fixture(self.fixture(root), dry_run=False, lane_path=lane, queue_path=root / "queue.json")

        self.assertIn("failing intake-agent on host 198", lane.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
