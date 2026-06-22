from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory_git_bridge import build_report, collect_notes, path_is_allowed


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


class MemoryGitBridgeTests(unittest.TestCase):
    def test_path_filter_allows_only_markdown_and_blocks_secret_paths(self):
        self.assertTrue(path_is_allowed("00_MEMORY/NEXT.md"))
        self.assertFalse(path_is_allowed("00_MEMORY/NEXT.txt"))
        self.assertFalse(path_is_allowed("00_MEMORY/private/NEXT.md"))
        self.assertFalse(path_is_allowed("00_MEMORY/api-key-plan.md"))
        self.assertFalse(path_is_allowed("../outside.md"))

    def test_collect_notes_uses_committed_markdown_paths(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _git(repo, "init", "-b", "main")
            _git(repo, "config", "user.email", "codex@example.test")
            _git(repo, "config", "user.name", "Codex")
            (repo / "README.md").write_text("# Existing\n", encoding="utf-8")
            _git(repo, "add", "README.md")
            _git(repo, "commit", "-m", "initial")

            (repo / "signal.md").write_text("# Phone-only signal\nThis file answers d021 proof.\n", encoding="utf-8")
            (repo / "ignore.txt").write_text("not markdown\n", encoding="utf-8")
            _git(repo, "add", "signal.md", "ignore.txt")
            _git(repo, "commit", "-m", "add signal")

            notes = collect_notes(repo)

        self.assertEqual([note.source_path for note in notes], ["memory-git/signal.md"])
        self.assertIn("Phone-only signal", notes[0].content)
        self.assertIn("memory-git", notes[0].tags)
        self.assertIn("personal", notes[0].tags)

    def test_collect_notes_skips_secret_content_before_network(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _git(repo, "init", "-b", "main")
            _git(repo, "config", "user.email", "codex@example.test")
            _git(repo, "config", "user.name", "Codex")
            (repo / "public.md").write_text("# Public\nOk for RAG.\n", encoding="utf-8")
            (repo / "secret.md").write_text("# Secret\npassword: hunter22\n", encoding="utf-8")
            _git(repo, "add", "public.md", "secret.md")
            _git(repo, "commit", "-m", "add notes")

            notes = collect_notes(repo)

        self.assertEqual([note.source_path for note in notes], ["memory-git/public.md"])

    def test_build_report_is_json_safe_and_redacts_content(self):
        note = mock.Mock()
        note.source_path = "memory-git/test.md"
        note.content = "content"
        report = build_report([note], [{"rows_written": 1}], dry_run=True)

        encoded = json.dumps(report)

        self.assertIn("memory-git/test.md", encoded)
        self.assertNotIn('"content": "content"', encoded)
        self.assertEqual(report["notes"], 1)


if __name__ == "__main__":
    unittest.main()
