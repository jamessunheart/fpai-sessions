from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.academy import distill


class AcademyDistillTest(unittest.TestCase):
    def test_renders_principles_cautions_and_playbooks_with_evidence(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-academy-"))
        proofs = root / "proofs"
        proofs.mkdir()
        (proofs / "proof.md").write_text(
            "# Proof One\n\n- Intent solved: activation checks became measurable.\n",
            encoding="utf-8",
        )
        ledger = root / "ops.jsonl"
        ledger.write_text(
            json.dumps(
                {
                    "event": "feature_outcome",
                    "spec_id": "SPEC_good",
                    "metric_name": "activation_quality",
                    "baseline": "merged_before_activation",
                    "observed": "activated",
                    "delta": "activation completed",
                    "verdict": "improved",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "event": "feature_outcome",
                    "spec_id": "SPEC_bad",
                    "metric_name": "liveness",
                    "baseline": "merged_before_activation",
                    "observed": "dead",
                    "delta": "runtime regression detected",
                    "verdict": "regressed",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        consequence = root / "CONSEQUENCE_REPORT.md"
        consequence.write_text(
            "# Consequence Report\n\n"
            "### SPEC_realized\n"
            "- verdict: `realized`\n"
            "- intent solved: proof returns as better intelligence.\n",
            encoding="utf-8",
        )
        output = root / "ACADEMY.md"

        text = distill.distill_academy(
            proofs_dir=proofs,
            ops_ledger=ledger,
            consequence_report=consequence,
            corrections=[
                {
                    "original_response": "Overclaim success.",
                    "james_correction": "Only call it a principle when evidence is traced.",
                    "captured_at": "2026-06-30T00:00:00Z",
                }
            ],
            output=output,
        )

        self.assertIn("## Principles (worked)", text)
        self.assertIn("SPEC_good", text)
        self.assertIn("## Cautions (regressed)", text)
        self.assertIn("SPEC_bad", text)
        self.assertIn("James correction", text)
        self.assertIn("## Playbooks (reusable)", text)
        for line in text.splitlines():
            if line.startswith("- ") and "No principles yet" not in line and "No regressed" not in line and "No reusable" not in line and "None." not in line:
                self.assertIn("[evidence:", line)
        self.assertEqual(output.read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()
