from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.doctrine import ingest


class DoctrineIngestTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-doctrine-ingest-"))
        state = root / "core" / "STATE"
        state.mkdir(parents=True)
        for rel_path in ingest.DOCTRINE_FILES:
            path = root / rel_path
            path.write_text(f"# {path.stem}\n\nAllocator role and P21 fixture.\n", encoding="utf-8")
        return root

    def test_collects_only_canonical_doctrine_with_freshness_metadata(self) -> None:
        repo = self.make_repo()

        with mock.patch.object(ingest, "current_commit", return_value="abcdef1234567890"):
            notes = ingest.collect_doctrine_notes(repo)

        self.assertEqual(len(ingest.DOCTRINE_FILES), len(notes))
        self.assertTrue(all(note.source_path.startswith("repo-doctrine/core/STATE/") for note in notes))
        self.assertTrue(all("doctrine" in note.tags for note in notes))
        core = next(note for note in notes if note.rel_path.endswith("CORE_DOCTRINE.md"))
        self.assertIn("**Doctrine source:** `core/STATE/CORE_DOCTRINE.md`", core.content)
        self.assertIn("**Repo commit:** `abcdef123456`", core.content)
        self.assertIn("**File updated:**", core.content)
        self.assertIn("**Freshness rule:**", core.content)

    def test_rejects_non_doctrine_paths(self) -> None:
        repo = self.make_repo()
        extra = repo / "core" / "STATE" / "SECRET.md"
        extra.write_text("# SECRET\n", encoding="utf-8")

        self.assertIsNone(ingest.load_doctrine_note(repo, "core/STATE/SECRET.md", "abc"))

    def test_dry_run_json_reports_repo_doctrine_source_paths(self) -> None:
        repo = self.make_repo()

        with mock.patch.object(ingest, "current_commit", return_value="abcdef1234567890"), mock.patch(
            "sys.stdout"
        ) as stdout:
            rc = ingest.main(["--repo", str(repo), "--dry-run", "--json"])

        self.assertEqual(0, rc)
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        data = json.loads(output)
        self.assertTrue(data["dry_run"])
        self.assertIn("repo-doctrine/core/STATE/ALLOCATION_INTELLIGENCE.md", data["source_paths"])

    def test_missing_token_blocks_live_write(self) -> None:
        repo = self.make_repo()

        with mock.patch.object(ingest, "current_commit", return_value="abcdef1234567890"), mock.patch("sys.stderr"):
            rc = ingest.main(["--repo", str(repo), "--token", ""])

        self.assertEqual(2, rc)


if __name__ == "__main__":
    unittest.main()
