from __future__ import annotations

import datetime as dt
import importlib.util
import asyncio
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

VERIFY_PATH = Path(__file__).with_name("verify_awareness.py")
VERIFY_SPEC = importlib.util.spec_from_file_location("verify_awareness", VERIFY_PATH)
assert VERIFY_SPEC and VERIFY_SPEC.loader
verify_awareness = importlib.util.module_from_spec(VERIFY_SPEC)
sys.modules["verify_awareness"] = verify_awareness
VERIFY_SPEC.loader.exec_module(verify_awareness)

MODULE_PATH = Path(__file__).with_name("reliability_probe.py")
SPEC = importlib.util.spec_from_file_location("reliability_probe", MODULE_PATH)
assert SPEC and SPEC.loader
reliability_probe = importlib.util.module_from_spec(SPEC)
sys.modules["reliability_probe"] = reliability_probe
SPEC.loader.exec_module(reliability_probe)

NOW = dt.datetime(2026, 6, 18, 12, 0, tzinfo=dt.timezone.utc)


class AwarenessReliabilityProbeTest(unittest.TestCase):
    def test_latest_session_insight_lookup_orders_by_timestamp(self) -> None:
        executed: list[str] = []

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def execute(self, sql):
                executed.append(sql)

            def fetchone(self):
                return (
                    444,
                    "session-latest",
                    "claude_code",
                    "architecture",
                    "D181 newest timestamp insight",
                    "Newest row must be the probe target even at low weight.",
                    ["d181"],
                    1,
                    "2026-07-04T19:00:00Z",
                )

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def cursor(self):
                return FakeCursor()

        fake_psycopg = types.SimpleNamespace(connect=lambda *_args, **_kwargs: FakeConnection())

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            latest = verify_awareness.latest_session_insight("postgres://example")

        self.assertEqual(latest["title"], "D181 newest timestamp insight")
        self.assertIn("ORDER BY ts DESC", executed[0])
        self.assertNotIn("ORDER BY weight DESC", executed[0])

    def test_behavioral_probe_asks_bot_and_grades_answer_keywords(self) -> None:
        latest = {
            "id": 444,
            "session_id": "session-latest",
            "surface": "claude_code",
            "insight_type": "architecture",
            "title": "D183 replace awareness with behavioral probe",
            "body": "The title-string proxy is broken; the bot must answer a factual question.",
            "specs_affected": ["d183"],
            "weight": 1,
            "ts": "2026-07-04T19:00:00Z",
        }
        asked: list[str] = []

        async def answerer(question: str) -> str:
            asked.append(question)
            return "It is about replacing the broken title proxy with a behavioral bot-answer probe for d183."

        async def continuity() -> verify_awareness.AwarenessProbe:
            return verify_awareness.AwarenessProbe(True, context_render_continuity=True)

        with patch.object(verify_awareness, "latest_session_insight", return_value=latest):
            result = asyncio.run(
                verify_awareness.verify_bot_response(
                    db_url="postgres://example",
                    bot_answerer=answerer,
                    context_probe=continuity,
                )
            )

        self.assertTrue(result.ok)
        self.assertTrue(result.behavioral_pass)
        self.assertTrue(result.context_render_continuity)
        self.assertEqual(asked, [result.question])
        self.assertIn("behavioral", result.matched_keywords)
        self.assertIn("probe", result.matched_keywords)

    def test_behavioral_probe_fails_when_answer_misses_latest_fact(self) -> None:
        latest = {
            "title": "D183 replace awareness with behavioral probe",
            "body": "The title-string proxy is broken.",
            "specs_affected": ["d183"],
            "ts": "2026-07-04T19:00:00Z",
        }

        async def answerer(_question: str) -> str:
            return "The system is generally operational."

        with patch.object(verify_awareness, "latest_session_insight", return_value=latest):
            result = asyncio.run(
                verify_awareness.verify_bot_response(db_url="postgres://example", bot_answerer=answerer)
            )

        self.assertFalse(result.ok)
        self.assertFalse(result.behavioral_pass)
        self.assertEqual(result.matched_keywords, ())
        self.assertIn("did not match", result.reason)

    def test_records_success_metric_without_alert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            async def verifier():
                return verify_awareness.AwarenessProbe(
                    True,
                    latest_title="d183 behavioral",
                    question="what changed?",
                    answer="behavioral probe",
                    matched_keywords=("behavioral", "probe"),
                    behavioral_pass=True,
                    context_render_continuity=False,
                )

            alerts: list[str] = []
            metric = reliability_probe.run(
                repo_root=root,
                ops_ledger=root / "ops.jsonl",
                json_path=root / "metric.json",
                markdown_path=root / "metric.md",
                cooldown_file=root / ".cooldown",
                now=NOW,
                verifier=verifier,
                notifier=lambda _repo, message: alerts.append(message) or True,
                send_alert_flag=True,
            )

            self.assertTrue(metric.ok)
            self.assertEqual(metric.reliability, 1.0)
            self.assertTrue(metric.behavioral_pass)
            self.assertFalse(metric.context_render_continuity)
            self.assertEqual(alerts, [])
            row = json.loads((root / "ops.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["event"], "awareness_reliability_probe")
            self.assertTrue(row["ok"])
            self.assertTrue(row["behavioral_pass"])
            self.assertFalse(row["context_render_continuity"])
            report = json.loads((root / "metric.json").read_text(encoding="utf-8"))
            self.assertTrue(report["metric"]["behavioral_pass"])

    def test_alerts_when_behavioral_reliability_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ops.jsonl"
            rows = [
                {
                    "ts": "2026-06-18T09:00:00Z",
                    "event": "awareness_reliability_probe",
                    "ok": True,
                    "reason": "old title proxy row ignored",
                },
                {
                    "ts": "2026-06-18T10:00:00Z",
                    "event": "awareness_reliability_probe",
                    "ok": True,
                    "behavioral_pass": True,
                },
                {
                    "ts": "2026-06-18T11:00:00Z",
                    "event": "awareness_reliability_probe",
                    "ok": False,
                    "behavioral_pass": False,
                },
            ]
            ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

            async def verifier():
                return verify_awareness.AwarenessProbe(
                    False,
                    reason="bot answer did not match latest session insight",
                    behavioral_pass=False,
                    context_render_continuity=True,
                )

            alerts: list[str] = []
            metric = reliability_probe.run(
                repo_root=root,
                ops_ledger=ledger,
                json_path=root / "metric.json",
                markdown_path=root / "metric.md",
                cooldown_file=root / ".cooldown",
                now=NOW,
                verifier=verifier,
                notifier=lambda _repo, message: alerts.append(message) or True,
                send_alert_flag=True,
            )

            self.assertFalse(metric.ok)
            self.assertAlmostEqual(metric.reliability, 1 / 3)
            self.assertTrue(metric.alert_sent)
            self.assertEqual(len(alerts), 1)
            self.assertIn("Behavioral awareness reliability below threshold", alerts[0])
            self.assertIn("Context-render continuity: True", alerts[0])
            self.assertTrue((root / ".cooldown").exists())

    def test_alert_cooldown_requires_actual_sent_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            async def verifier():
                return verify_awareness.AwarenessProbe(False, reason="no active session_insights rows found")

            metric = reliability_probe.run(
                repo_root=root,
                ops_ledger=root / "ops.jsonl",
                json_path=root / "metric.json",
                markdown_path=root / "metric.md",
                cooldown_file=root / ".cooldown",
                now=NOW,
                verifier=verifier,
                notifier=lambda _repo, _message: False,
                send_alert_flag=True,
            )

            self.assertFalse(metric.alert_sent)
            self.assertFalse((root / ".cooldown").exists())

    def test_cooldown_blocks_repeated_alerts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".cooldown").write_text("2026-06-18T11:45:00Z", encoding="utf-8")

            async def verifier():
                return verify_awareness.AwarenessProbe(False, reason="missing")

            alerts: list[str] = []
            metric = reliability_probe.run(
                repo_root=root,
                ops_ledger=root / "ops.jsonl",
                json_path=root / "metric.json",
                markdown_path=root / "metric.md",
                cooldown_file=root / ".cooldown",
                now=NOW,
                verifier=verifier,
                notifier=lambda _repo, message: alerts.append(message) or True,
                send_alert_flag=True,
            )

            self.assertFalse(metric.ok)
            self.assertFalse(metric.alert_sent)
            self.assertEqual(alerts, [])


if __name__ == "__main__":
    unittest.main()
