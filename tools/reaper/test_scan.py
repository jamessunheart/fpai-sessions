from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.reaper import scan


class ReaperScanTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-reaper-test-"))
        subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        return root

    def commit_all(self, root: Path, message: str, date: str) -> None:
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
        subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, env=env, stdout=subprocess.PIPE)

    def test_report_lists_stale_service_and_tracked_artifact_without_mutating(self) -> None:
        root = self.make_repo()
        service = root / "SERVICES" / "stale"
        service.mkdir(parents=True)
        (service / "app.py").write_text("print('old')\n", encoding="utf-8")
        artifact = root / "SERVICES" / "stale" / "venv" / "bin"
        artifact.mkdir(parents=True)
        (artifact / "python").write_text("binary-ish\n", encoding="utf-8")
        self.commit_all(root, "old service and artifact", "2025-01-01T00:00:00+0000")
        before_files = sorted(
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.parts
        )

        report = scan.build_report(
            repo=root,
            output=root / "docs" / "codex" / "REAPER_REPORT.md",
            size_threshold_mb=1,
            stale_days=90,
            systemd_units=[{"name": "stale.service", "state": "running", "path": "SERVICES/stale"}],
        )

        self.assertIn("SERVICES/stale", report)
        self.assertIn("zero-commit-90d", report)
        self.assertIn("SERVICES/stale/venv", report)
        self.assertIn("tracked-artifact", report)
        self.assertIn("REPORT ONLY", report)
        self.assertIn("venv/", report)
        after_files = sorted(
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.parts
        )
        self.assertTrue((root / "SERVICES" / "stale" / "venv" / "bin" / "python").exists())
        self.assertIn(Path("docs/codex/REAPER_REPORT.md"), after_files)
        self.assertTrue(set(before_files).issubset(set(after_files)))

    def test_dry_run_matches_normal_report_shape(self) -> None:
        root = self.make_repo()
        dist = root / "app" / "dist"
        dist.mkdir(parents=True)
        (dist / "bundle.js").write_text("x" * 2048, encoding="utf-8")
        self.commit_all(root, "tracked dist", "2025-01-01T00:00:00+0000")

        normal = scan.build_report(
            repo=root,
            output=root / "normal.md",
            size_threshold_mb=1,
            systemd_units=[],
            dry_run=False,
        )
        dry = scan.build_report(
            repo=root,
            output=root / "dry.md",
            size_threshold_mb=1,
            systemd_units=[],
            dry_run=True,
        )

        self.assertIn("app/dist", normal)
        self.assertIn("app/dist", dry)
        self.assertIn("No files were deleted.", dry)
        self.assertEqual(normal.split("## Ranked Kill-List Candidates", 1)[1].split("## Guardrails", 1)[0],
                         dry.split("## Ranked Kill-List Candidates", 1)[1].split("## Guardrails", 1)[0])


if __name__ == "__main__":
    unittest.main()
