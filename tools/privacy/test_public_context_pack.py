from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.privacy.public_context_pack import PublicDecision, build_public_context_pack


class PublicContextPackTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-public-pack-"))
        (root / "core" / "STATE").mkdir(parents=True)
        (root / "docs" / "blueprints").mkdir(parents=True)
        (root / "core" / "STATE" / "NORTH_STAR.md").write_text(
            "# FPOS North Star\nPublic mission and sovereign efficiency targets.\n",
            encoding="utf-8",
        )
        (root / "docs" / "blueprints" / "spark.md").write_text(
            "# Spark\nPublic capability: turns signal into a useful first response.\n",
            encoding="utf-8",
        )
        (root / "private").mkdir()
        (root / "private" / "tg_messages.txt").write_text(
            "SECRET_PRIVATE_THREAD correction wallet balance location",
            encoding="utf-8",
        )
        return root

    def test_pack_contains_only_allowed_public_context(self) -> None:
        pack = build_public_context_pack(
            repo_root=self.make_repo(),
            include_db_decisions=False,
            decisions=[PublicDecision("d-public", "This result is public proof.", "Shipped.")],
        )

        self.assertIn("FPOS North Star", pack)
        self.assertIn("Spark", pack)
        self.assertIn("d-public", pack)
        self.assertNotIn("SECRET_PRIVATE_THREAD", pack)
        self.assertNotIn("tg_messages.txt", pack)

    def test_pack_is_bounded_under_two_thousand_chars(self) -> None:
        root = self.make_repo()
        (root / "docs" / "blueprints" / "large.md").write_text("# Large\n" + ("public " * 1000), encoding="utf-8")

        pack = build_public_context_pack(repo_root=root, include_db_decisions=False)

        self.assertLessEqual(len(pack), 1900)

    def test_output_excludes_private_table_names(self) -> None:
        pack = build_public_context_pack(repo_root=self.make_repo(), include_db_decisions=False)

        for forbidden in ("tg_messages", "corrections", "thread", "note_chunks", "user_profiles", "probe_sessions"):
            self.assertNotIn(forbidden, pack)


if __name__ == "__main__":
    unittest.main()

