from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.hot_memory.scanners import signal_scanner


class SignalScannerTest(unittest.TestCase):
    def test_liveness_failures_become_hot_signal_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "core" / "STATE").mkdir(parents=True)
            ledger = root / "ops_ledger.jsonl"
            ledger.write_text(
                json.dumps(
                    {
                        "ts": "2026-06-18T21:40:00Z",
                        "loop": "liveness",
                        "event": "liveness:fail",
                        "detail": "SPEC_d115 rc=1 log=/opt/fpai-build/logs/SPEC_d115.liveness.log",
                        "artifact": "build/SPEC_d115",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            facts = signal_scanner.collect(repo_root=root, db_url="", ops_ledger=ledger)

        rendered = [fact.text for fact in facts]
        self.assertTrue(any("Post-merge liveness failure" in text for text in rendered))
        self.assertTrue(any("SPEC_d115" in text for text in rendered))


if __name__ == "__main__":
    unittest.main()
