#!/usr/bin/env python3
"""Static contract tests for persisted build_status=changes rework."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_loop" / "server_build_loop.sh"


class ChangesReworkLoopContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_changes_rows_get_a_dedicated_rework_pass(self) -> None:
        self.assertIn("CHANGES REWORK PASS", self.text)
        self.assertIn("changes_rework_candidates", self.text)
        self.assertIn("process_changes_rework", self.text)
        self.assertIn("run_revision_agent_attempt \"$REWORK_ATTEMPT\" \"$REVIEW_FILE\"", self.text)
        self.assertIn("tools/merge/ai_review.py \"$BR\"", self.text)
        self.assertIn("Stay on branch $BR", self.text)

    def test_rework_attempts_self_migrate_and_cap_at_two(self) -> None:
        self.assertIn('REWORK_ATTEMPT_LIMIT="${REWORK_ATTEMPT_LIMIT:-2}"', self.text)
        self.assertIn("DRY RUN — skipping rework_attempts migration and capped-row blocking", self.text)
        self.assertIn("ADD COLUMN IF NOT EXISTS rework_attempts INTEGER DEFAULT 0", self.text)
        self.assertIn("SET rework_attempts = 0", self.text)
        self.assertIn("SET rework_attempts = COALESCE(rework_attempts, 0) + 1", self.text)
        self.assertIn("COALESCE(rework_attempts, 0) < %s", self.text)
        self.assertIn("COALESCE(rework_attempts, 0) >= %s", self.text)
        self.assertIn("SET build_status = 'blocked'", self.text)

    def test_second_still_flagged_rework_blocks_not_loops(self) -> None:
        self.assertIn('elif [ "$REWORK_ATTEMPT" -ge "$REWORK_ATTEMPT_LIMIT" ]; then', self.text)
        self.assertIn("ST=blocked", self.text)
        self.assertIn("reviewer still flags changes after $REWORK_ATTEMPT_LIMIT attempts", self.text)
        self.assertIn("Ember/James: council review $DID", self.text)

    def test_backlog_merge_excludes_changes_status(self) -> None:
        backlog_start = self.text.index("BACKLOG_JSON=")
        backlog_end = self.text.index("while IFS= read -r bline", backlog_start)
        backlog_query = self.text[backlog_start:backlog_end]
        self.assertIn("['built']", backlog_query)
        self.assertNotIn("'changes','built'", backlog_query)
        self.assertNotIn("WORKTREE_BRANCHES=", backlog_query)


if __name__ == "__main__":
    unittest.main()
