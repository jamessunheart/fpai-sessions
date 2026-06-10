from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.apprentice.artifact import render_review_artifact, write_review_artifact


class ApprenticeArtifactTest(unittest.TestCase):
    def sample_payload(self) -> dict:
        return {
            "selected_intent": {
                "id": "results-bottleneck-session",
                "title": "Bottleneck Session",
                "stream": "Ventures",
                "source_next": "Name 3-5 warm leads",
            },
            "apprentice_dry_run": {"status": "gated"},
            "would_do": [
                {
                    "step": "draft candidate leads",
                    "action": "draft-review-artifact",
                }
            ],
            "would_pause_at": {
                "step": "approve and send these 5",
                "reason": "matched Public / outbound send: send",
                "gate": {
                    "question": "Reserved-Class blessing needed: approve and send these 5",
                    "verbs": ["approve", "reject", "checkpoint"],
                },
            },
            "why": "The apprentice pauses only at the Reserved-Class send step.",
        }

    def test_render_review_artifact_names_work_and_gate(self) -> None:
        text = render_review_artifact(self.sample_payload())

        self.assertIn("Apprentice Review", text)
        self.assertIn("draft candidate leads", text)
        self.assertIn("approve and send these 5", text)
        self.assertIn("not an approval", text)

    def test_write_review_artifact_creates_markdown(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-apprentice-artifact-"))
        path = write_review_artifact(self.sample_payload(), root / "review.md")

        self.assertTrue(path.exists())
        self.assertIn("Bottleneck Session", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
