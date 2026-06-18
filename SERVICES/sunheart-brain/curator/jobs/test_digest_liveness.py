import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from curator import liveness_status


class DigestLivenessTest(unittest.TestCase):
    def test_liveness_honest_map_reports_running_partial_planned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ops.jsonl"
            rows = [
                {
                    "event": "liveness:pass",
                    "liveness_status": "live",
                    "spec_id": "SPEC_d115_live",
                    "detail": "SPEC_d115_live live",
                },
                {
                    "event": "liveness:partial",
                    "liveness_status": "partial",
                    "spec_id": "SPEC_d117_partial",
                    "detail": "SPEC_d117_partial partial: file live; port dead",
                },
                {
                    "event": "liveness:planned",
                    "liveness_status": "planned",
                    "spec_id": "SPEC_d118_planned",
                    "detail": "SPEC_d118_planned planned",
                },
            ]
            ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

            lines = liveness_status.liveness_honest_map_lines(ledger)

        self.assertEqual(lines[0], "Liveness map: running=1 | partial=1 | dead=0 | planned=1")
        self.assertTrue(any("SPEC_d117_partial: partial" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
