from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.learn import capture_corrections as capture


class CaptureCorrectionsTest(unittest.TestCase):
    def test_pair_uses_d010_compatible_shape(self) -> None:
        row = capture.make_correction_pair(
            rejected="Ask James for every small decision.",
            preferred="Pick the reversible default and tell James the rollback.",
            prompt="What should we do next?",
            captured_at="2026-06-15T00:00:00+00:00",
        )

        self.assertTrue(row["id"].startswith("corr-"))
        self.assertEqual(row["signal"], "james_correction")
        self.assertEqual(row["verdict"], "correction")
        self.assertEqual(row["split"], "train")
        self.assertIs(row["never_train"], False)
        self.assertIsNone(row["eval"])
        self.assertEqual(row["preferred"]["text"], "Pick the reversible default and tell James the rollback.")
        self.assertEqual(row["rejected"]["text"], "Ask James for every small decision.")

    def test_append_pair_dedupes_by_default(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-corrections-"))
        dataset = root / "preference_pairs.jsonl"
        row = capture.make_correction_pair(rejected="old", preferred="new", captured_at="2026-06-15T00:00:00+00:00")

        self.assertTrue(capture.append_pair(row, dataset))
        self.assertFalse(capture.append_pair(row, dataset))

        rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], row["id"])

    def test_cli_appends_to_requested_dataset(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-corrections-cli-"))
        dataset = root / "pairs.jsonl"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(capture.__file__)),
                "--dataset",
                str(dataset),
                "--prompt",
                "original context",
                "--rejected",
                "stale bot answer",
                "--preferred",
                "current build context answer",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        result = json.loads(proc.stdout)
        self.assertTrue(result["wrote"])
        rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["prompt"], "original context")


if __name__ == "__main__":
    unittest.main()

