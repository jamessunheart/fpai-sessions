from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

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
    def test_records_success_metric_without_alert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            async def verifier():
                return verify_awareness.AwarenessProbe(True, latest_title="d110 visible")

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
            self.assertEqual(alerts, [])
            row = json.loads((root / "ops.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["event"], "awareness_reliability_probe")
            self.assertTrue(row["ok"])

    def test_alerts_when_rolling_reliability_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ops.jsonl"
            rows = [
                {"ts": "2026-06-18T10:00:00Z", "event": "awareness_reliability_probe", "ok": True},
                {"ts": "2026-06-18T11:00:00Z", "event": "awareness_reliability_probe", "ok": False},
            ]
            ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

            async def verifier():
                return verify_awareness.AwarenessProbe(False, reason="latest title missing from bot context")

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
            self.assertIn("Awareness reliability below threshold", alerts[0])
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
