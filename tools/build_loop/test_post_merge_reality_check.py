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


class ContextConn(FakeConn):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


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

    def test_mark_merged_dead_annotates_reality_status_only(self) -> None:
        # 2026-07-02: mark_merged_dead must ONLY write the reality_status
        # (liveness) annotation — never touch build_status, and never
        # auto-queue a repair spec. See mark_merged_dead docstring.
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
        # No repair spec queued (was the 100%-FP spam bomb).
        self.assertEqual(conn.inserted, [])
        # build_status must NOT be WRITTEN (build/merge axis untouched). It may
        # appear in the WHERE read-guard, but never in the SET clause.
        update_sql = conn.executed[0][0]
        set_clause = update_sql.split(" where ", 1)[0]
        self.assertNotIn("build_status", set_clause)
        self.assertNotIn("needs_build", set_clause)
        self.assertIn("reality_status", set_clause)

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
        self.assertEqual(row["loop"], "post_merge_reality")
        self.assertEqual(row["merged_dead"], 1)
        self.assertEqual(row["marked"], ["d131"])

    def test_dry_run_does_not_trip_circuit_when_live_proof_dead_rate_below_half(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ops.jsonl"
            decisions = [
                check.MergedDecision(
                    decision_id="d141",
                    question="d141 live",
                    build_branch="build/SPEC_d141_live",
                    build_spec="",
                    proof_expected="metric moved",
                    liveness="",
                    merged_at=dt.datetime(2026, 6, 28, tzinfo=dt.timezone.utc),
                ),
                check.MergedDecision(
                    decision_id="d142",
                    question="d142 live",
                    build_branch="build/SPEC_d142_live",
                    build_spec="",
                    proof_expected="metric moved",
                    liveness="",
                    merged_at=dt.datetime(2026, 6, 28, tzinfo=dt.timezone.utc),
                ),
                check.MergedDecision(
                    decision_id="d143",
                    question="d143 dead",
                    build_branch="build/SPEC_d143_dead",
                    build_spec="",
                    proof_expected="metric moved",
                    liveness="",
                    merged_at=dt.datetime(2026, 6, 28, tzinfo=dt.timezone.utc),
                ),
            ]
            rows = [
                {"event": "liveness:pass", "spec_id": "SPEC_d141_live", "liveness_status": "live"},
                {"event": "feature_outcome", "spec_id": "SPEC_d141_live", "verdict": "improved"},
                {"event": "liveness:pass", "spec_id": "SPEC_d142_live", "liveness_status": "live"},
                {"event": "feature_outcome", "spec_id": "SPEC_d142_live", "verdict": "improved"},
            ]
            ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            old_connect = check.connect
            old_fetch = check.fetch_merged_decisions
            try:
                check.connect = lambda: ContextConn()  # type: ignore[assignment]
                check.fetch_merged_decisions = lambda conn, now, grace_days: decisions  # type: ignore[assignment]
                result = check.run_check(
                    ops_ledger=ledger,
                    dry_run=True,
                    now=dt.datetime(2026, 7, 2, tzinfo=dt.timezone.utc),
                )
            finally:
                check.connect = old_connect  # type: ignore[assignment]
                check.fetch_merged_decisions = old_fetch  # type: ignore[assignment]

        self.assertNotIn("circuit_breaker", result)
        self.assertEqual(result["checked"], 3)
        self.assertEqual([item["status"] for item in result["verdicts"]].count("merged_dead"), 1)


class PostMergeRealityShellContractTest(unittest.TestCase):
    def test_dedicated_systemd_timer_runs_checker_daily_at_0330_utc(self) -> None:
        service = (check.REPO_ROOT / "core/BUILD/cron/fpai-post-merge-reality.service").read_text(encoding="utf-8")
        timer = (check.REPO_ROOT / "core/BUILD/cron/fpai-post-merge-reality.timer").read_text(encoding="utf-8")

        self.assertIn("post_merge_reality_check.py", service)
        self.assertIn("FPAI_SURFACE=systemd:fpai-post-merge-reality", service)
        self.assertIn("POST_MERGE_REALITY_CHECK_DISABLE", service)
        self.assertIn("--ops-ledger", service)
        self.assertIn("--send-alert", service)
        self.assertIn("OnCalendar=*-*-* 03:30:00 UTC", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("Unit=fpai-post-merge-reality.service", timer)

    def test_activation_installs_and_enables_dedicated_timer(self) -> None:
        activate = (check.REPO_ROOT / "core/BUILD/activate/SPEC_d150_swarm-verified-wire-post-merge.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("fpai-post-merge-reality.service", activate)
        self.assertIn("fpai-post-merge-reality.timer", activate)
        self.assertIn("systemctl daemon-reload", activate)
        self.assertIn("systemctl enable --now fpai-post-merge-reality.timer", activate)
        self.assertIn("systemctl disable --now fpai-post-merge-reality.timer", activate)

    def test_server_build_loop_no_longer_owns_post_merge_reality_cadence(self) -> None:
        text = (check.REPO_ROOT / "tools/build_loop/server_build_loop.sh").read_text(encoding="utf-8")

        self.assertNotIn("run_post_merge_reality_check_daily", text)
        self.assertNotIn(".post_merge_reality_check_day", text)

    def test_decision_cli_stamps_merged_at_for_existing_mark_merged_call_shape(self) -> None:
        decisions = (check.REPO_ROOT / "SERVICES/sunheart-brain/curator/decisions.py").read_text(encoding="utf-8")

        self.assertIn("ADD COLUMN IF NOT EXISTS merged_at TIMESTAMPTZ", decisions)
        self.assertIn("merged_at = CASE WHEN %s = 'merged'", decisions)
        self.assertIn('return mark_merged(args[1], args[2] if len(args) >= 3 else "ok")', decisions)


if __name__ == "__main__":
    unittest.main()
