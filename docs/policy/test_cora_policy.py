from __future__ import annotations

import re
import unittest
from pathlib import Path


POLICY_PATH = Path(__file__).with_name("CORA_POLICY_v0.2.md")


class CoraPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = POLICY_PATH.read_text(encoding="utf-8")

    def test_all_required_sections_are_present(self) -> None:
        required_sections = [
            "## 1. What CORA Is",
            "## 2. What Earns CORA",
            "## 3. What Backs CORA",
            "## 4. What Spends/Burns CORA",
            "## 5. Issuance Caps",
            "## 6. What CORA Cannot Do",
            "## 7. Decay and Renewal",
            "## 8. Gap Log",
        ]

        for section in required_sections:
            with self.subTest(section=section):
                self.assertIn(section, self.text)

    def test_legal_containment_includes_all_required_cannot_do_items(self) -> None:
        legal_section = self._section("## 6. What CORA Cannot Do")
        required_items = [
            "CORA cannot be converted to cash or fiat.",
            "CORA cannot be traded on secondary markets.",
            "CORA cannot be used as investment language.",
            "CORA cannot be sold directly.",
            "CORA is not a security, not a token, not a cryptocurrency.",
            "CORA expires after 12 months of account inactivity.",
            "CORA is non-transferable between accounts.",
        ]

        for item in required_items:
            with self.subTest(item=item):
                self.assertIn(item, legal_section)

    def test_gap_log_is_non_empty(self) -> None:
        gap_log = self._section("## 8. Gap Log")
        bullets = [line for line in gap_log.splitlines() if line.startswith("- ")]
        self.assertGreaterEqual(len(bullets), 4)
        self.assertIn("Compliance/legal review status is not complete.", gap_log)

    def _section(self, heading: str) -> str:
        pattern = rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^## \d+\. |\Z)"
        match = re.search(pattern, self.text, flags=re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(match, f"missing section: {heading}")
        return match.group("body")


if __name__ == "__main__":
    unittest.main()
