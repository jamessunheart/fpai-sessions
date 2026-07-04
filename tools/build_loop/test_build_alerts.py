#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.build_loop import build_alerts


UTC = dt.timezone.utc


class BuildAlertsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="fpai-build-alerts-"))
        self.paths = build_alerts.AlertPaths(
            stats=self.root / "build_stats.json",
            state=self.root / "build_alert_state.json",
            digest=self.root / "build_alert_digest.json",
        )

    def test_start_uses_honest_eta_from_median_and_p90(self) -> None:
        self.paths.stats.write_text(
            json.dumps(
                {
                    "entries": [
                        {"duration_seconds": 300},
                        {"duration_seconds": 360},
                        {"duration_seconds": 420},
                        {"duration_seconds": 480},
                        {"duration_seconds": 1200},
                    ]
                }
            ),
            encoding="utf-8",
        )

        msg = build_alerts.event_message(
            "start",
            "d155",
            "SPEC_d155_demo",
            "Build lifecycle alerts",
            paths=self.paths,
            now=dt.datetime(2026, 7, 4, 15, 0, tzinfo=UTC),
        )

        self.assertEqual(msg, "▶️ BUILD START d155 Build lifecycle alerts · ETA ~7m, p90 20m")
        state = json.loads(self.paths.state.read_text(encoding="utf-8"))
        self.assertEqual(state["builds"]["SPEC_d155_demo"]["stage"], "building")

    def test_merged_records_duration_stat(self) -> None:
        start = dt.datetime(2026, 7, 4, 15, 0, tzinfo=UTC)
        end = dt.datetime(2026, 7, 4, 15, 8, tzinfo=UTC)
        build_alerts.event_message("start", "d155", "SPEC_d155_demo", "Lifecycle alerts", paths=self.paths, now=start)

        msg = build_alerts.event_message("merged", "d155", "SPEC_d155_demo", "Lifecycle alerts", paths=self.paths, now=end)

        self.assertEqual(msg, "✅ MERGED d155 · took 8m · Lifecycle alerts")
        stats = json.loads(self.paths.stats.read_text(encoding="utf-8"))
        self.assertEqual(stats["entries"][-1]["duration_seconds"], 480)
        self.assertEqual(stats["entries"][-1]["outcome"], "merged")

    def test_burst_batches_after_three_recent_sent_events(self) -> None:
        now = dt.datetime(2026, 7, 4, 15, 0, tzinfo=UTC)
        digest = {
            "sent_starts": [
                {"ts": "2026-07-04T14:40:00Z", "spec_id": "a"},
                {"ts": "2026-07-04T14:45:00Z", "spec_id": "b"},
                {"ts": "2026-07-04T14:50:00Z", "spec_id": "c"},
            ],
            "pending": [],
        }
        self.paths.digest.write_text(json.dumps(digest), encoding="utf-8")

        msg = build_alerts.event_message("start", "d155", "SPEC_d155_demo", "Lifecycle alerts", paths=self.paths, now=now)

        self.assertEqual(msg, "")
        pending = json.loads(self.paths.digest.read_text(encoding="utf-8"))["pending"]
        self.assertEqual(len(pending), 1)
        self.assertIn("BUILD START d155", pending[0]["message"])

        review_msg = build_alerts.event_message(
            "review",
            "d155",
            "SPEC_d155_demo",
            "Lifecycle alerts",
            paths=self.paths,
            now=now + dt.timedelta(minutes=1),
        )

        self.assertEqual(review_msg, "")
        pending = json.loads(self.paths.digest.read_text(encoding="utf-8"))["pending"]
        self.assertEqual(len(pending), 2)
        self.assertIn("REVIEW d155", pending[1]["message"])

    def test_failed_bypasses_quiet_hours_batch(self) -> None:
        quiet = dt.datetime(2026, 7, 4, 4, 30, tzinfo=UTC)  # 22:30 CR previous day

        msg = build_alerts.event_message(
            "failed",
            "d155",
            "SPEC_d155_demo",
            "Lifecycle alerts",
            "review blocked",
            paths=self.paths,
            now=quiet,
        )

        self.assertEqual(msg, "❌ FAILED d155 · review blocked")

    def test_disabled_mode_returns_no_message_or_files(self) -> None:
        with mock.patch.dict("os.environ", {"BUILD_ALERTS": "0"}):
            msg = build_alerts.event_message(
                "start",
                "d155",
                "SPEC_d155_demo",
                "Lifecycle alerts",
                paths=self.paths,
                now=dt.datetime(2026, 7, 4, 15, 0, tzinfo=UTC),
            )

        self.assertEqual(msg, "")
        self.assertFalse(self.paths.state.exists())

    def test_heartbeat_updates_alert_state_file(self) -> None:
        now = dt.datetime(2026, 7, 4, 15, 0, tzinfo=UTC)

        build_alerts.heartbeat(paths=self.paths, now=now)

        state = json.loads(self.paths.state.read_text(encoding="utf-8"))
        self.assertEqual(state["last_heartbeat_at"], "2026-07-04T15:00:00Z")

    def test_queue_snapshot_reports_pending_inflight_and_today(self) -> None:
        repo = self.root / "repo"
        specs = repo / "core" / "BUILD" / "specs"
        results = repo / "core" / "BUILD" / "results"
        specs.mkdir(parents=True)
        results.mkdir(parents=True)
        (specs / "SPEC_d155_demo.md").write_text("# spec\n", encoding="utf-8")
        registry = repo / "core" / "BUILD" / "REGISTRY.json"
        registry.write_text(json.dumps({"active_builds": []}), encoding="utf-8")
        self.paths.state.write_text(
            json.dumps({"builds": {"SPEC_d155_demo": {"decision_id": "d155", "stage": "review"}}}),
            encoding="utf-8",
        )
        self.paths.stats.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "spec_id": "SPEC_d154_demo",
                            "completed_at": "2026-07-04T15:10:00Z",
                            "duration_seconds": 600,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        text = build_alerts.render_queue_snapshot(
            repo,
            paths=self.paths,
            now=dt.datetime(2026, 7, 4, 16, 0, tzinfo=UTC),
        )

        self.assertIn("pending: <b>1</b> · d155", text)
        self.assertIn("in flight: d155: review", text)
        self.assertIn("completed today: <b>1</b>", text)
        self.assertIn("ETA ~10m", text)


if __name__ == "__main__":
    unittest.main()
