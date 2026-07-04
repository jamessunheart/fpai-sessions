#!/usr/bin/env python3
"""Static contract tests for server build-loop parallelism."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from tools.build_loop import build_state


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_loop" / "server_build_loop.sh"


class ParallelBuildLoopContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_default_concurrency_is_three_and_can_be_serialized(self) -> None:
        self.assertIn('BUILD_CONCURRENCY="${BUILD_CONCURRENCY:-3}"', self.text)
        self.assertIn('"$BUILD_CONCURRENCY" -lt 1', self.text)
        self.assertIn('while [ "$(jobs -pr | wc -l | tr -d \' \')" -ge "$BUILD_CONCURRENCY" ]', self.text)
        self.assertIn('process_pending_build "$line" &', self.text)

    def test_pending_query_excludes_claimed_building_rows(self) -> None:
        self.assertIn("building", build_state.BUILT_DECISION_STATUSES)
        self.assertIn("'building'", build_state.PENDING_DECISION_WHERE_SQL)
        rows = [
            {"id": "d001", "status": "answered", "needs_build": True, "build_status": "building"},
            {"id": "d002", "status": "answered", "needs_build": True},
        ]
        self.assertEqual([row["id"] for row in build_state.pending_builds_from_rows(rows)], ["d002"])

    def test_build_is_claimed_atomically_before_worker_spawn(self) -> None:
        self.assertIn("claim_pending_build()", self.text)
        self.assertIn("UPDATE brain_index.decisions", self.text)
        self.assertIn("SET build_status = 'building'", self.text)
        self.assertIn("RETURNING id::text", self.text)
        claim_pos = self.text.index('claim_pending_build "$_DID" "$_BR"')
        spawn_pos = self.text.index('process_pending_build "$line" &')
        self.assertLess(claim_pos, spawn_pos)

    def test_codex_build_has_timeout(self) -> None:
        self.assertIn('BUILD_TIMEOUT="${BUILD_TIMEOUT:-90m}"', self.text)
        self.assertIn('timeout "$BUILD_TIMEOUT" codex exec --cd "$WT" --full-auto -', self.text)
        self.assertIn('codex timed out after $BUILD_TIMEOUT', self.text)
        self.assertIn('ops_log.py" build timeout', self.text)

    def test_approved_merges_are_serialized_with_flock(self) -> None:
        self.assertIn('MERGE_LOCKFILE="${MERGE_LOCKFILE:-/opt/fpai-build/.merge.lock}"', self.text)
        self.assertGreaterEqual(self.text.count("flock -x 9"), 2)
        merge_pattern = re.compile(r"flock -x 9.*?git -C \"\$REPO\" merge --no-edit \"\$BR\"", re.S)
        backlog_pattern = re.compile(r"flock -x 9.*?git -C \"\$REPO\" merge --no-edit \"\$BBR\"", re.S)
        self.assertRegex(self.text, merge_pattern)
        self.assertRegex(self.text, backlog_pattern)


if __name__ == "__main__":
    unittest.main()
