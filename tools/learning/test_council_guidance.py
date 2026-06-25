from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.learning import council_guidance


class CouncilGuidanceTest(unittest.TestCase):
    def test_produces_weighting_directive_json(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-directive-"))
        output = root / "directive.json"

        directive = council_guidance.produce_weighting_directive(
            metrics={"regressions": 1, "weak_tasks": 2, "engagement_delta": 0.1},
            signal_counts={"approval": 10, "correction": 2},
            output_path=output,
        )

        saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "directive_ready")
        self.assertGreater(directive["weighting"]["reversal"], council_guidance.DEFAULT_WEIGHTS["reversal"])
        self.assertLess(directive["weighting"]["approval"], council_guidance.DEFAULT_WEIGHTS["approval"])


if __name__ == "__main__":
    unittest.main()
