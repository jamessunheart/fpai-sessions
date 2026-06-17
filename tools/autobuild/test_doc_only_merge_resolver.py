#!/usr/bin/env python3
"""Tests for tools.autobuild.doc_only_merge_resolver."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.autobuild import doc_only_merge_resolver as resolver


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class AutoMergeDocOnlyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.extra_files: list[Path] = []
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-b", "feat/headless-build")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test Bot")
        (self.root / "core/BUILD").mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / "tools").mkdir()
        (self.root / "tools/merge").mkdir(parents=True)
        (self.root / "tools/merge/pre_merge_snapshot.sh").write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -eu
                BASE="${1:-feat/headless-build}"
                PREFIX="${MERGE_SNAPSHOT_PREFIX:-fpai/pre-merge/}"
                SHA="$(git rev-parse "$BASE")"
                EXISTING="$(git tag --points-at "$SHA" --list "${PREFIX}[0-9][0-9][0-9][0-9]" | sort -V | tail -1 || true)"
                if [ -n "$EXISTING" ]; then echo "$EXISTING"; exit 0; fi
                LATEST="$(git tag --list "${PREFIX}[0-9][0-9][0-9][0-9]" | sort -V | tail -1 || true)"
                if [ -n "$LATEST" ]; then NUM="${LATEST##*/}"; NEXT=$((10#$NUM + 1)); else NEXT=1; fi
                TAG="$(printf '%s%04d' "$PREFIX" "$NEXT")"
                git tag "$TAG" "$SHA"
                echo "$TAG"
                """
            )
        )
        (self.root / "tools/merge/pre_merge_snapshot.sh").chmod(0o755)
        (self.root / "docs/start.md").write_text("# start\n")
        self.registry = self.root / "core/BUILD/REGISTRY.json"
        self.registry.write_text(json.dumps({"active_builds": []}))
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "base")
        self.review = self.root / "approve_review.py"
        self.review.write_text("#!/usr/bin/env python3\nimport sys\nprint('APPROVE:', sys.argv[-1])\n")
        self.review.chmod(0o755)
        git(self.root, "add", str(self.review.relative_to(self.root)))
        git(self.root, "commit", "-m", "review helper")

    def tearDown(self) -> None:
        for path in self.extra_files:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        self.tmp.cleanup()

    def write_registry(self, branch: str, *, tests_passed: bool = True, status: str = "done") -> None:
        self.registry.write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": branch.replace("/", "-"),
                            "branch": branch,
                            "base_branch": "feat/headless-build",
                            "status": status,
                            "tests_passed": tests_passed,
                        }
                    ]
                }
            )
        )
        git(self.root, "add", str(self.registry.relative_to(self.root)))
        git(self.root, "commit", "-m", "registry")

    def make_branch(self, branch: str, path: str, content: str) -> None:
        git(self.root, "checkout", "-b", branch)
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        git(self.root, "add", path)
        git(self.root, "commit", "-m", f"change {path}")
        git(self.root, "checkout", "feat/headless-build")

    def resolve(self, *, execute: bool = False, branch: str | None = None) -> list[resolver.CandidateResult]:
        return resolver.resolve(
            root=self.root,
            registry=self.registry,
            base="feat/headless-build",
            review_command=[str(self.review)],
            execute=execute,
            branch_filter=branch,
        )

    def test_dry_run_finds_doc_only_candidate(self) -> None:
        self.make_branch("build/doc", "docs/guide.md", "# guide\n")
        self.write_registry("build/doc")

        results = self.resolve()

        self.assertEqual("would_merge", results[0].action)
        self.assertEqual(["docs/guide.md"], results[0].changed_files)

    def test_blocks_code_paths_before_review(self) -> None:
        self.make_branch("build/code", "tools/new_tool.py", "print('no')\n")
        self.write_registry("build/code")

        results = self.resolve()

        self.assertEqual("block", results[0].action)
        self.assertIn("tools/new_tool.py", results[0].reason)

    def test_blocks_general_state_json(self) -> None:
        self.make_branch("build/state", "core/STATE/policy.json", "{}\n")
        self.write_registry("build/state")

        results = self.resolve()

        self.assertEqual("block", results[0].action)
        self.assertIn("core/STATE/policy.json", results[0].reason)

    def test_blocks_build_intake_paths(self) -> None:
        self.make_branch("build/spec", "core/BUILD/specs/SPEC_new.md", "# spec\n")
        self.write_registry("build/spec")

        results = self.resolve()

        self.assertEqual("block", results[0].action)
        self.assertIn("core/BUILD/specs/SPEC_new.md", results[0].reason)

    def test_execute_merges_after_review_command_approves(self) -> None:
        self.make_branch("build/doc", "docs/guide.md", "# guide\n")
        self.write_registry("build/doc")

        results = self.resolve(execute=True, branch="build/doc")

        self.assertEqual("merged", results[0].action)
        log = git(self.root, "log", "--oneline", "--max-count=1").stdout
        self.assertIn("auto-merge doc-only AI-approved branch", log)
        self.assertTrue((self.root / "docs/guide.md").exists())
        tags = git(self.root, "tag", "--list", "fpai/pre-merge/*").stdout.splitlines()
        self.assertEqual(["fpai/pre-merge/0001"], tags)

    def test_execute_blocks_if_review_command_fails(self) -> None:
        fd, failing_name = tempfile.mkstemp(prefix="fail_review_", suffix=".py")
        os.close(fd)
        failing_review = Path(failing_name)
        self.extra_files.append(failing_review)
        failing_review.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import sys
                print("REQUEST_CHANGES:", sys.argv[-1])
                raise SystemExit(1)
                """
            )
        )
        failing_review.chmod(0o755)
        self.make_branch("build/doc", "docs/guide.md", "# guide\n")
        self.write_registry("build/doc")

        results = resolver.resolve(
            root=self.root,
            registry=self.registry,
            base="feat/headless-build",
            review_command=[str(failing_review)],
            execute=True,
            branch_filter="build/doc",
        )

        self.assertEqual("block", results[0].action)
        self.assertIn("independent AI review did not approve", results[0].reason)
        self.assertFalse((self.root / "docs/guide.md").exists())

    def test_execute_refuses_dirty_worktree(self) -> None:
        self.make_branch("build/doc", "docs/guide.md", "# guide\n")
        self.write_registry("build/doc")
        (self.root / "untracked.txt").write_text("dirty\n")

        with self.assertRaisesRegex(resolver.ResolverError, "dirty worktree"):
            self.resolve(execute=True, branch="build/doc")

    def test_execute_refuses_main_base(self) -> None:
        self.make_branch("build/doc", "docs/guide.md", "# guide\n")
        self.write_registry("build/doc")

        with self.assertRaisesRegex(resolver.ResolverError, "protected base branch"):
            resolver.resolve(
                root=self.root,
                registry=self.registry,
                base="main",
                review_command=[str(self.review)],
                execute=True,
                branch_filter="build/doc",
            )

    def test_execute_aborts_failed_merge(self) -> None:
        self.make_branch("build/doc", "docs/start.md", "branch version\n")
        self.write_registry("build/doc")
        (self.root / "docs/start.md").write_text("base version\n")
        git(self.root, "add", "docs/start.md")
        git(self.root, "commit", "-m", "base conflicting edit")

        with self.assertRaisesRegex(resolver.ResolverError, "merge"):
            self.resolve(execute=True, branch="build/doc")

        status = git(self.root, "status", "--porcelain").stdout
        self.assertEqual("", status)
        current = git(self.root, "branch", "--show-current").stdout.strip()
        self.assertEqual("feat/headless-build", current)

    def test_skips_entries_that_are_not_done_with_tests(self) -> None:
        self.make_branch("build/doc", "docs/guide.md", "# guide\n")
        self.write_registry("build/doc", tests_passed=False)

        self.assertEqual([], self.resolve())


if __name__ == "__main__":
    unittest.main()
