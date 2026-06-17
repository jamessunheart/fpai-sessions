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

    def write_registry(
        self,
        branch: str,
        *,
        build_id: str | None = None,
        tests_passed: bool = True,
        status: str = "done",
    ) -> None:
        self.registry.write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": build_id or branch.replace("/", "-"),
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
        self.make_branch_changes(branch, {path: content})

    def make_branch_changes(self, branch: str, changes: dict[str, str]) -> None:
        git(self.root, "checkout", "-b", branch)
        for path, content in changes.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            git(self.root, "add", path)
        git(self.root, "commit", "-m", "change candidate files")
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
        self.assertEqual("doc-only", results[0].policy)
        self.assertEqual(["docs/guide.md"], results[0].changed_files)

    def test_dry_run_finds_safety_build_candidate(self) -> None:
        build_id = "SPEC_d077_auto-revert-on-break"
        self.make_branch_changes(
            "build/safety",
            {
                "tools/autobuild/auto_revert.py": "print('guard')\n",
                "tools/autobuild/test_auto_revert.py": "print('test')\n",
                "tools/build_loop/build_orchestrator.sh": "#!/usr/bin/env bash\n",
                f"core/BUILD/specs/{build_id}.md": "# safety spec\n",
                f"core/BUILD/results/{build_id}.result.md": "# result\n",
                "docs/codex/HANDOFF.md": "# handoff\n",
            },
        )
        self.write_registry("build/safety", build_id=build_id)

        results = self.resolve()

        self.assertEqual("would_merge", results[0].action)
        self.assertEqual("safety-build", results[0].policy)
        self.assertIn("tools/autobuild/auto_revert.py", results[0].changed_files)
        self.assertIn("tools/build_loop/build_orchestrator.sh", results[0].changed_files)

    def test_blocks_code_paths_before_review(self) -> None:
        self.make_branch("build/code", "tools/new_tool.py", "print('no')\n")
        self.write_registry("build/code")

        results = self.resolve()

        self.assertEqual("block", results[0].action)
        self.assertIn("tools/new_tool.py", results[0].reason)

    def test_blocks_non_autobuild_tool_paths_even_for_safety_builds(self) -> None:
        build_id = "SPEC_d077_auto-revert-on-break"
        self.make_branch_changes(
            "build/safety",
            {
                "tools/autobuild/auto_revert.py": "print('guard')\n",
                "tools/merge/merge_gate.sh": "# unsafe scope\n",
            },
        )
        self.write_registry("build/safety", build_id=build_id)

        results = self.resolve()

        self.assertEqual("block", results[0].action)
        self.assertIn("tools/merge/merge_gate.sh", results[0].reason)

    def test_blocks_other_build_specs_from_safety_policy(self) -> None:
        build_id = "SPEC_d077_auto-revert-on-break"
        self.make_branch_changes(
            "build/safety",
            {
                "tools/autobuild/auto_revert.py": "print('guard')\n",
                "core/BUILD/specs/SPEC_other.md": "# unrelated spec\n",
            },
        )
        self.write_registry("build/safety", build_id=build_id)

        results = self.resolve()

        self.assertEqual("block", results[0].action)
        self.assertIn("core/BUILD/specs/SPEC_other.md", results[0].reason)

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
        self.assertIn("auto-merge AI-approved low-risk branch", log)
        self.assertTrue((self.root / "docs/guide.md").exists())

    def test_execute_merges_safety_build_after_review_command_approves(self) -> None:
        build_id = "SPEC_d077_auto-revert-on-break"
        self.make_branch_changes(
            "build/safety",
            {
                "tools/autobuild/auto_revert.py": "print('guard')\n",
                f"core/BUILD/specs/{build_id}.md": "# safety spec\n",
                f"core/BUILD/results/{build_id}.result.md": "# result\n",
            },
        )
        self.write_registry("build/safety", build_id=build_id)

        results = self.resolve(execute=True, branch="build/safety")

        self.assertEqual("merged", results[0].action)
        self.assertEqual("safety-build", results[0].policy)
        self.assertTrue((self.root / "tools/autobuild/auto_revert.py").exists())

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
