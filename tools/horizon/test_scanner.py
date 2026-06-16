from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.horizon import scanner


NOW = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)


class HorizonScannerTest(unittest.TestCase):
    def write_config(self, root: Path) -> Path:
        path = root / "horizon_config.json"
        path.write_text(
            json.dumps(
                {
                    "energy_low_days_threshold": 3,
                    "build_stall_repeat_threshold": 2,
                    "revert_streak_threshold": 3,
                    "topic_recurrence_threshold": 3,
                    "silence_hours_threshold": 24,
                    "active_hours_utc": [6, 20],
                }
            ),
            encoding="utf-8",
        )
        return path

    def run_with(
        self,
        root: Path,
        *,
        streams: dict | None = None,
        ops_rows: list[dict] | None = None,
        registry_state: dict | None = None,
        sender=None,
        composer=None,
    ) -> scanner.ScanResult:
        return scanner.run_scan(
            config_path=self.write_config(root),
            ops_ledger=root / "ops_ledger.jsonl",
            disable_file=root / ".horizon_disabled",
            now=NOW,
            streams=streams or {"life_events": [], "decisions": [], "thread": [], "tg_messages": []},
            ops_rows=ops_rows or [],
            registry_state=registry_state or {"counts": {}, "queued_specs": []},
            sender=sender or (lambda _message: True),
            composer=composer or scanner.fallback_message,
        )

    def test_three_days_low_energy_detects_energy_low_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = [
                {"date": "2026-06-14", "energy": 2},
                {"date": "2026-06-15", "energy": 3},
                {"date": "2026-06-16", "text": "low energy"},
            ]
            result = self.run_with(root, streams={"life_events": events, "decisions": [], "thread": [], "tg_messages": []})
            self.assertTrue(result.signal)
            self.assertIn("energy_low", {s.kind for s in result.signals})

    def test_two_blocked_decisions_detects_stall_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = [
                {"decision_id": "d034", "title": "Hermes", "status": "blocked"},
                {"decision_id": "d034", "title": "Hermes", "status": "blocked"},
            ]
            result = self.run_with(root, streams={"life_events": [], "decisions": decisions, "thread": [], "tg_messages": []})
            self.assertTrue(result.signal)
            self.assertEqual(result.selected.kind, "build_stall")
            self.assertIn("d034", result.message)

    def test_no_thresholds_crossed_writes_no_signal_and_sends_nothing(self) -> None:
        sent: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_with(
                root,
                streams={
                    "life_events": [{"date": "2026-06-16", "energy": 7}],
                    "decisions": [],
                    "thread": [{"at": NOW.isoformat(), "text": "hello"}],
                    "tg_messages": [],
                },
                sender=lambda message: sent.append(message) or True,
            )
            self.assertFalse(result.signal)
            self.assertEqual(sent, [])
            rows = [json.loads(line) for line in (root / "ops_ledger.jsonl").read_text().splitlines()]
            self.assertEqual(rows[-1]["event"], "horizon_scan")
            self.assertEqual(rows[-1]["signal"], "no")

    def test_cross_signal_energy_low_plus_builds_queued_mentions_both_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = [
                {"date": "2026-06-14", "energy": 2},
                {"date": "2026-06-15", "energy": 2},
                {"date": "2026-06-16", "energy": 3},
            ]
            result = self.run_with(
                root,
                streams={"life_events": events, "decisions": [], "thread": [], "tg_messages": []},
                registry_state={"counts": {"queued": 4}, "queued_specs": []},
            )
            self.assertEqual(result.selected.kind, "energy_low_build_load")
            self.assertIn("Low energy", result.message)
            self.assertIn("builds", result.message)

    def test_ops_ledger_write_on_every_scan_regardless_of_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_streams = {
                "life_events": [],
                "decisions": [],
                "thread": [{"at": NOW.isoformat(), "text": "hello"}],
                "tg_messages": [],
            }
            self.run_with(root, streams=active_streams)
            self.run_with(
                root,
                streams={"life_events": [{"date": "2026-06-14", "energy": 2}, {"date": "2026-06-15", "energy": 2}, {"date": "2026-06-16", "energy": 2}], "decisions": [], "thread": [], "tg_messages": []},
            )
            rows = [json.loads(line) for line in (root / "ops_ledger.jsonl").read_text().splitlines()]
            self.assertEqual([row["signal"] for row in rows], ["no", "yes"])

    def test_complete_silence_detects_silence_when_source_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_with(root)
            self.assertTrue(result.signal)
            self.assertEqual(result.selected.kind, "silence")
            self.assertIn("No interaction rows", result.message)

    def test_proposal_drought_detected_when_queue_exists_without_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_with(
                root,
                streams={"life_events": [], "decisions": [], "thread": [{"at": NOW.isoformat(), "text": "hello"}], "tg_messages": []},
                registry_state={"counts": {"queued": 1}, "queued_specs": []},
                ops_rows=[],
            )
            self.assertIn("proposal_drought", {s.kind for s in result.signals})

    def test_probe_sessions_detect_drop_rate_and_quality_decline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            probes = [
                {"initiated_at": (NOW - timedelta(hours=i)).isoformat(), "engaged": i == 0, "completed_spark": False, "quality_score": 0.2}
                for i in range(5)
            ]
            result = self.run_with(
                root,
                streams={"life_events": [], "decisions": [], "thread": [{"at": NOW.isoformat(), "text": "hello"}], "tg_messages": [], "probe_sessions": probes},
            )
            kinds = {s.kind for s in result.signals}
            self.assertIn("probe_drop_rate_spike", kinds)
            self.assertIn("probe_quality_declining", kinds)

    def test_default_send_telegram_false_when_notifier_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "tools" / "build_loop" / "notify_telegram.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\necho 'notify: token/chat missing (skipped)'\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            self.assertFalse(scanner.default_send_telegram("hello", repo_root=root))

    def test_tg_message_is_max_three_sentences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_with(
                root,
                streams={"life_events": [{"date": "2026-06-14", "energy": 2}, {"date": "2026-06-15", "energy": 2}, {"date": "2026-06-16", "energy": 2}], "decisions": [], "thread": [], "tg_messages": []},
                composer=lambda _signal: "One. Two. Three. Four.",
            )
            self.assertLessEqual(scanner.sentence_count(result.message or ""), 3)
            self.assertEqual(result.message, "One. Two. Three.")

    def test_horizon_disable_exits_without_scanning(self) -> None:
        old = os.environ.get("HORIZON_DISABLE")
        os.environ["HORIZON_DISABLE"] = "1"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = self.run_with(root, sender=lambda _message: self.fail("should not send"))
                self.assertTrue(result.disabled)
                self.assertFalse((root / "ops_ledger.jsonl").exists())
        finally:
            if old is None:
                os.environ.pop("HORIZON_DISABLE", None)
            else:
                os.environ["HORIZON_DISABLE"] = old

    def test_recent_horizon_signal_lines_only_includes_signal_yes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ops_ledger.jsonl"
            rows = [
                {"ts": (NOW - timedelta(hours=1)).isoformat(), "event": "horizon_scan", "signal": "no", "detail": {"pattern": None}},
                {"ts": (NOW - timedelta(hours=2)).isoformat(), "event": "horizon_scan", "signal": "yes", "detail": {"pattern": "Low energy flagged 3 days"}},
                {"ts": (NOW - timedelta(days=2)).isoformat(), "event": "horizon_scan", "signal": "yes", "detail": {"pattern": "Old"}},
            ]
            ledger.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            self.assertEqual(
                scanner.recent_horizon_signal_lines(ledger, now=NOW),
                ["2026-06-16 10:00 · Low energy flagged 3 days"],
            )


if __name__ == "__main__":
    unittest.main()
