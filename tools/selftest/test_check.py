from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.selftest import check


class SelftestCheckTestCase(unittest.TestCase):
    def make_roots(self) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="fpai-selftest-"))
        repo = root / "repo"
        vault = root / "vault"
        (repo / "docs" / "codex" / "specs").mkdir(parents=True)
        (vault / "00_MEMORY").mkdir(parents=True)
        return repo, vault

    def test_home_next_parser(self) -> None:
        text = """# HOME

## ▶️ NEXT MOVE

**Go autonomous — run the self-standing one-day test?**

**Tell:** Claude Code / Ember.
"""
        self.assertEqual(
            check.parse_home_next(text),
            "Go autonomous — run the self-standing one-day test?",
        )

    def test_latest_proof_requires_buildstream_fields(self) -> None:
        _, vault = self.make_roots()
        (vault / "00_MEMORY" / "PROOF LOG.md").write_text(
            "# PROOF LOG\n\n---\n\n"
            "- 2026-06-06 18:07 MDT · [Game] · Intent solved: test · Unlocks next: self-standing one-day test · Proof: ok · Next move: go autonomous\n",
            encoding="utf-8",
        )

        result = check.check_proof(vault)

        self.assertEqual(result.status, check.PASS)

    def test_home_buildstream_agreement(self) -> None:
        repo, vault = self.make_roots()
        (vault / "HOME.md").write_text(
            "# HOME\n\n## ▶️ NEXT MOVE\n\n**Go autonomous — run the self-standing one-day test?**\n",
            encoding="utf-8",
        )
        (vault / "00_MEMORY" / "INTENT BUILDSTREAM.md").write_text(
            "# Intent Buildstream\n"
            "<!-- INTENTS:START -->\n"
            "- id:rung3 | value:5 | unlocks:test | status:done | Rung 3 Auto-routing\n"
            "- id:test | value:5 | unlocks:resources | status:ready | Self-standing one-day test\n"
            "<!-- INTENTS:END -->\n",
            encoding="utf-8",
        )

        result = check.check_home_buildstream(repo, vault)

        self.assertEqual(result.status, check.PASS)

    def test_phone_cloud_docs_warns_when_missing(self) -> None:
        repo, _ = self.make_roots()

        result = check.check_phone_cloud_docs(repo)

        self.assertEqual(result.status, check.WARN)
        self.assertIn("AGENTS.md", result.evidence)


if __name__ == "__main__":
    unittest.main()
