#!/usr/bin/env python3
"""Static contract tests for server_build_loop.sh revision-agent control flow."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_loop" / "server_build_loop.sh"


class RevisionAgentShellContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_flagged_only_revision_loop_has_kill_switch_and_two_attempt_cap(self):
        self.assertIn('if [ "$RC" != 0 ] && [ "$RC" != 2 ]; then', self.text)
        self.assertIn('REVISION_AGENT_DISABLE:-0', self.text)
        self.assertIn('"$REVISION_ATTEMPT" -lt 2', self.text)
        self.assertIn("Revision agent: flagged review gets up to 2", self.text)

    def test_revision_prompt_is_constrained_to_reviewer_findings(self):
        self.assertIn("Fix ONLY the specific issues flagged", self.text)
        self.assertIn("Original spec:", self.text)
        self.assertIn("$SPEC", self.text)
        self.assertIn("Reviewer feedback:", self.text)
        self.assertIn("$feedback", self.text)
        self.assertIn("Do not broaden scope", self.text)

    def test_revision_uses_review_file_and_same_worktree_codex(self):
        self.assertIn("review_file_for_branch", self.text)
        self.assertIn("review_findings", self.text)
        self.assertIn('REVIEW_FILE="$(review_file_for_branch "$BR")"', self.text)
        self.assertIn('codex exec --cd "$WT" --full-auto -', self.text)
        self.assertIn('$SPECID.revision-$attempt.codex.log', self.text)

    def test_revision_commits_then_reruns_independent_review(self):
        self.assertIn('commit -q -m "build($SPECID): revision agent pass $attempt"', self.text)
        review_calls = re.findall(r'tools/merge/ai_review\.py "\$BR"', self.text)
        self.assertGreaterEqual(len(review_calls), 2)
        self.assertIn("revision approved", self.text)
        self.assertIn("revision still-flagged", self.text)

    def test_revision_attempts_are_ops_logged(self):
        for event in (
            "revision attempted",
            "revision committed",
            "revision no-changes",
            "revision skipped",
            "revision approved",
            "revision still-flagged",
            "revision blocked",
            "revision fallback-auto-merge",
        ):
            self.assertIn(event, self.text)


if __name__ == "__main__":
    unittest.main()
