from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.apprentice.ledger import append_ledger, ledger_row


class ApprenticeLedgerTest(unittest.TestCase):
    def sample_payload(self) -> dict:
        return {
            "selected_intent": {
                "id": "results-bottleneck-session",
                "title": "Bottleneck Session",
                "stream": "Ventures",
            },
            "apprentice_dry_run": {"status": "gated"},
            "would_do": [{"step": "draft candidate leads", "action": "draft-review-artifact"}],
            "would_pause_at": {
                "step": "approve and send these 5",
                "reason": "matched Public / outbound send: send",
                "gate": {"question": "Reserved-Class blessing needed: approve and send these 5"},
            },
            "artifact_path": "/private/tmp/review.md",
        }

    def test_ledger_row_keeps_review_summary(self) -> None:
        row = ledger_row(self.sample_payload())

        self.assertEqual(row["intent_id"], "results-bottleneck-session")
        self.assertEqual(row["would_do"][0]["step"], "draft candidate leads")
        self.assertEqual(row["would_pause_at"], "approve and send these 5")
        self.assertEqual(row["artifact_path"], "/private/tmp/review.md")

    def test_append_ledger_writes_jsonl_only_when_called(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-apprentice-ledger-"))
        ledger = append_ledger(self.sample_payload(), root / "ledger.jsonl")

        rows = ledger.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), 1)
        parsed = json.loads(rows[0])
        self.assertEqual(parsed["intent_id"], "results-bottleneck-session")


if __name__ == "__main__":
    unittest.main()
