#!/usr/bin/env python3
"""Tests for tools.autobuild.auto_revert."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.autobuild import auto_revert


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class AutoRevertTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-b", "feat/headless-build")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test Bot")
        (self.root / "app.txt").write_text("good\n", encoding="utf-8")
        git(self.root, "add", "app.txt")
        git(self.root, "commit", "-m", "known good")
        self.known_good = git(self.root, "rev-parse", "HEAD").stdout.strip()
        git(self.root, "checkout", "-b", "build/test")
        (self.root / "app.txt").write_text("candidate\n", encoding="utf-8")
        git(self.root, "commit", "-am", "candidate")
        self.report_dir = Path("core/BUILD/reports/auto_revert")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def guard(self, command: list[str], *, execute: bool = False, allow_dirty: bool = False) -> auto_revert.AutoRevertReport:
        return auto_revert.guard_build(
            root=self.root,
            known_good_ref=self.known_good,
            check_command=command,
            report_dir=self.report_dir,
            execute=execute,
            allow_dirty=allow_dirty,
        )

    def test_successful_check_does_not_rollback(self) -> None:
        report = self.guard(["python3", "-c", "print('ok')"], execute=True)

        self.assertEqual("ok", report.status)
        self.assertFalse(report.rollback_performed)
        self.assertEqual("candidate\n", (self.root / "app.txt").read_text(encoding="utf-8"))
        latest = json.loads((self.root / self.report_dir / "latest.json").read_text(encoding="utf-8"))
        self.assertEqual("ok", latest["status"])

    def test_failed_check_rolls_back_to_known_good_and_reports(self) -> None:
        report = self.guard(["python3", "-c", "import sys; print('broken'); sys.exit(7)"], execute=True)

        self.assertEqual("reverted", report.status)
        self.assertTrue(report.rollback_performed)
        self.assertEqual(7, report.check_returncode)
        self.assertTrue(report.failed_backup_ref.startswith("refs/fpai-auto-revert/"))
        self.assertEqual(self.known_good, report.post_revert_head_sha)
        self.assertTrue(report.post_revert_clean)
        self.assertEqual("good\n", (self.root / "app.txt").read_text(encoding="utf-8"))
        failed_diff = Path(report.failed_diff_path).read_text(encoding="utf-8")
        self.assertIn("candidate", failed_diff)
        backup = git(self.root, "rev-parse", report.failed_backup_ref).stdout.strip()
        self.assertEqual(report.failed_head_sha, backup)
        md = (self.root / self.report_dir / "latest.md").read_text(encoding="utf-8")
        self.assertIn("Status: reverted", md)
        self.assertIn("Failed backup ref", md)
        self.assertIn("broken", md)

    def test_failed_check_dry_run_reports_without_reset(self) -> None:
        report = self.guard(["python3", "-c", "raise SystemExit(3)"], execute=False)

        self.assertEqual("would_revert", report.status)
        self.assertFalse(report.rollback_performed)
        self.assertEqual("candidate\n", (self.root / "app.txt").read_text(encoding="utf-8"))
        self.assertTrue(Path(report.failed_diff_path).exists())

    def test_dirty_worktree_requires_explicit_allow_dirty(self) -> None:
        (self.root / "uncommitted.txt").write_text("generated\n", encoding="utf-8")

        with self.assertRaisesRegex(auto_revert.AutoRevertError, "uncommitted changes"):
            self.guard(["python3", "-c", "print('ok')"], execute=True)

    def test_allow_dirty_discards_uncommitted_build_output_on_failure(self) -> None:
        (self.root / "uncommitted.txt").write_text("generated\n", encoding="utf-8")

        report = self.guard(["python3", "-c", "raise SystemExit(1)"], execute=True, allow_dirty=True)

        self.assertEqual("reverted", report.status)
        self.assertFalse((self.root / "uncommitted.txt").exists())
        self.assertIn("uncommitted.txt", report.changed_files_before_revert)

    def test_refuses_protected_branch(self) -> None:
        git(self.root, "checkout", "-b", "main")

        with self.assertRaisesRegex(auto_revert.AutoRevertError, "protected branch"):
            self.guard(["python3", "-c", "print('ok')"], execute=True)

    def test_cli_returns_zero_after_successful_revert(self) -> None:
        script = self.root / "fail.py"
        script.write_text("raise SystemExit(4)\n", encoding="utf-8")

        proc = subprocess.run(
            [
                "python3",
                str(Path(auto_revert.__file__).resolve()),
                "--known-good",
                self.known_good,
                "--report-dir",
                str(self.report_dir),
                "--execute",
                "--allow-dirty",
                "--",
                "python3",
                str(script),
            ],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("reverted", proc.stdout)
        self.assertEqual("good\n", (self.root / "app.txt").read_text(encoding="utf-8"))

    def test_cli_repo_root_targets_build_worktree_from_other_cwd(self) -> None:
        parent = self.root.parent

        proc = subprocess.run(
            [
                "python3",
                str(Path(auto_revert.__file__).resolve()),
                "--repo-root",
                str(self.root),
                "--known-good",
                self.known_good,
                "--report-dir",
                str(self.report_dir),
                "--execute",
                "--fail-after-revert",
                "--",
                "python3",
                "-c",
                "raise SystemExit(6)",
            ],
            cwd=parent,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(6, proc.returncode)
        self.assertEqual("good\n", (self.root / "app.txt").read_text(encoding="utf-8"))

    def test_cli_can_fail_after_revert_for_orchestrator_accounting(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                str(Path(auto_revert.__file__).resolve()),
                "--known-good",
                self.known_good,
                "--report-dir",
                str(self.report_dir),
                "--execute",
                "--fail-after-revert",
                "--",
                "python3",
                "-c",
                "raise SystemExit(5)",
            ],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(5, proc.returncode)
        self.assertIn("reverted", proc.stdout)
        self.assertEqual("good\n", (self.root / "app.txt").read_text(encoding="utf-8"))

    def test_optional_ops_ledger_receives_reversed_row(self) -> None:
        ledger = self.root / "ops.jsonl"
        report = auto_revert.guard_build(
            root=self.root,
            known_good_ref=self.known_good,
            check_command=["python3", "-c", "raise SystemExit(2)"],
            report_dir=self.report_dir,
            execute=True,
            allow_dirty=False,
            ops_ledger=ledger,
        )

        self.assertTrue(report.rollback_performed)
        row = json.loads(ledger.read_text(encoding="utf-8").strip())
        self.assertEqual("auto_revert", row["loop"])
        self.assertEqual("reversed", row["event"])


class MarkdownRenderTest(unittest.TestCase):
    def test_report_ids_are_collision_resistant(self) -> None:
        ids = {auto_revert.make_report_id() for _ in range(100)}

        self.assertEqual(100, len(ids))

    def test_markdown_is_plain_ascii_and_mentions_next_review(self) -> None:
        report = auto_revert.AutoRevertReport(
            status="reverted",
            branch="build/x",
            known_good_ref="feat/headless-build",
            known_good_sha="abc123",
            failed_head_sha="def456",
            check_command=["python3", "-m", "unittest"],
            check_returncode=1,
            changed_files_before_revert=["tools/x.py"],
            rollback_performed=True,
            report_id="auto-revert-test",
            failed_backup_ref="refs/fpai-auto-revert/auto-revert-test",
            failed_diff_path="core/BUILD/reports/auto_revert/auto-revert-test.failed.diff",
            post_revert_head_sha="abc123",
            post_revert_clean=True,
            output_tail="failed",
            reason="verification failed; worktree reset to known good ref",
        )

        markdown = auto_revert.render_markdown(report)

        markdown.encode("ascii")
        self.assertIn("James/Ember should review", markdown)
        self.assertIn("tools/x.py", markdown)


if __name__ == "__main__":
    unittest.main()
