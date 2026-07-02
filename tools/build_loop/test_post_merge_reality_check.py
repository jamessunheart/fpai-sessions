from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from tools.build_loop import post_merge_reality_check as check


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if normalized.startswith("update brain_index.decisions"):
            self.rowcount = 1
            self.conn.updated.append(params)
            return
        if normalized.startswith("insert into brain_index.decisions"):
            self.rowcount = 1
            self.conn.inserted.append(params)
            return
        raise AssertionError(f"unexpected SQL: {sql}")


class FakeConn:
    def __init__(self):
        self.executed = []
        self.updated = []
        self.inserted = []

    def cursor(self):
        return FakeCursor(self)


class PostMergeRealityCheckTest(unittest.TestCase):
    def decision(self, merged_at: dt.datetime | None = None) -> check.MergedDecision:
        return check.MergedDecision(
            decision_id="d131",
            question="d131 question engine",
            build_branch="build/SPEC_d131_question-engine",
            build_spec="",
            proof_expected="metric moved",
            liveness="",
            merged_at=merged_at or dt.datetime(2026, 6, 28, tzinfo=dt.timezone.utc),
        )

    def test_real_requires_liveness_pass_and_improved_feature_outcome(self) -> None:
        decision = self.decision()
        rows = [
            {"ts": "2026-06-29T00:00:00Z", "event": "liveness:pass", "spec_id": decision.spec_id, "liveness_status": "live"},
            {"ts": "2026-06-30T00:00:00Z", "event": "feature_outcome", "spec_id": decision.spec_id, "verdict": "improved"},
        ]

        verdict = check.evaluate_decision(
            decision,
            rows,
            now=dt.datetime(2026, 7, 2, tzinfo=dt.timezone.utc),
            grace_days=3,
        )

        self.assertEqual(verdict.status, "real")
        self.assertTrue(verdict.evidence.live)
        self.assertTrue(verdict.evidence.metric_moved)

    def test_missing_metric_after_grace_marks_merged_dead(self) -> None:
        decision = self.decision()
        rows = [
            {"ts": "2026-06-29T00:00:00Z", "event": "liveness:pass", "spec_id": decision.spec_id, "liveness_status": "live"},
            {"ts": "2026-06-30T00:00:00Z", "event": "feature_outcome", "spec_id": decision.spec_id, "verdict": "flat"},
        ]

        verdict = check.evaluate_decision(
            decision,
            rows,
            now=dt.datetime(2026, 7, 2, tzinfo=dt.timezone.utc),
            grace_days=3,
        )

        self.assertEqual(verdict.status, "merged_dead")
        self.assertIn("metric movement proof", verdict.reason)

    def test_grace_window_waits_even_when_evidence_missing(self) -> None:
        decision = self.decision(dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc))

        verdict = check.evaluate_decision(
            decision,
            [],
            now=dt.datetime(2026, 7, 2, tzinfo=dt.timezone.utc),
            grace_days=3,
        )

        self.assertEqual(verdict.status, "pending")
        self.assertIn("grace", verdict.reason)

    def test_mark_merged_dead_updates_source_and_queues_one_repair_spec(self) -> None:
        decision = self.decision()
        verdict = check.RealityVerdict(
            decision=decision,
            age_days=4,
            status="merged_dead",
            evidence=check.LedgerEvidence(live=False, metric_moved=False),
            reason="missing LIVE artifact proof and metric movement proof",
        )
        conn = FakeConn()

        changed = check.mark_merged_dead(conn, verdict)

        self.assertTrue(changed)
        self.assertEqual(conn.updated[0][1], "d131")
        self.assertEqual(conn.inserted[0][0], "d131-reality-fix")
        self.assertIn("Repair merged-dead build d131", conn.inserted[0][1])
        self.assertIn("liveness:pass", conn.inserted[0][4])

    def test_ops_ledger_summary_records_marked_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ops.jsonl"
            decision = self.decision()
            verdict = check.RealityVerdict(
                decision=decision,
                age_days=4,
                status="merged_dead",
                evidence=check.LedgerEvidence(live=False, metric_moved=False),
                reason="missing proof",
            )

            check.append_ops_ledger(path, [verdict], ["d131"])

            row = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(row["event"], "post-merge-reality")
        self.assertEqual(row["merged_dead"], 1)
        self.assertEqual(row["marked"], ["d131"])


class PostMergeRealityShellContractTest(unittest.TestCase):
    def test_server_build_loop_runs_checker_once_per_day_from_health_pulse(self) -> None:
        text = (check.REPO_ROOT / "tools/build_loop/server_build_loop.sh").read_text(encoding="utf-8")

        health = text.index('ops_log.py" health "loop-pulse"')
        checker = text.index("run_post_merge_reality_check_daily", health)

        self.assertIn("POST_MERGE_REALITY_CHECK_DISABLE", text)
        self.assertIn("post_merge_reality_check.py", text)
        self.assertIn(".post_merge_reality_check_day", text)
        self.assertLess(health, checker)

    def test_decision_cli_stamps_merged_at_for_existing_mark_merged_call_shape(self) -> None:
        decisions = (check.REPO_ROOT / "SERVICES/sunheart-brain/curator/decisions.py").read_text(encoding="utf-8")

        self.assertIn("ADD COLUMN IF NOT EXISTS merged_at TIMESTAMPTZ", decisions)
        self.assertIn("merged_at = CASE WHEN %s = 'merged'", decisions)
        self.assertIn('return mark_merged(args[1], args[2] if len(args) >= 3 else "ok")', decisions)


if __name__ == "__main__":
    unittest.main()
