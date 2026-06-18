import json
import tempfile
import unittest
from pathlib import Path

from tools.liveness import probe


class FakeRunner:
    def __init__(self, statuses):
        self.statuses = statuses
        self.checked = []

    def check(self, item):
        self.checked.append(item)
        status, detail = self.statuses.get((item.kind, item.target), ("unknown", "fixture unknown"))
        return probe.CheckResult(item, status, detail)


class LivenessProbeTest(unittest.TestCase):
    def test_parse_yaml_liveness_block(self) -> None:
        text = """
## Build
Ship the thing.

liveness:
  - type: systemd
    unit: fpai-build-loop.timer
  - type: table
    table: brain_index.probe_sessions
  - type: file
    path: core/STATE/HOT_STATE.md
  - type: endpoint
    url: http://127.0.0.1:8000/health
  - type: port
    port: 127.0.0.1:5432

## Tests
"""

        checks = probe.parse_liveness(text)

        self.assertEqual([item.kind for item in checks], ["systemd", "table", "file", "endpoint", "port"])
        self.assertEqual(checks[0].target, "fpai-build-loop.timer")
        self.assertEqual(checks[1].target, "brain_index.probe_sessions")

    def test_parse_json_liveness(self) -> None:
        raw = json.dumps({"liveness": [{"type": "file", "path": "core/STATE/HOT_STATE.md"}]})

        checks = probe.parse_liveness(raw)

        self.assertEqual(checks, (probe.LivenessCheck("file", "core/STATE/HOT_STATE.md"),))

    def test_run_probe_classifies_live_partial_dead_and_planned(self) -> None:
        live = probe.run_probe(
            "liveness:\n  - file: core/live.txt\n",
            runner=FakeRunner({("file", "core/live.txt"): ("live", "exists")}),
        )
        partial = probe.run_probe(
            "liveness:\n  - file: core/live.txt\n  - port: 65500\n",
            runner=FakeRunner({
                ("file", "core/live.txt"): ("live", "exists"),
                ("port", "65500"): ("dead", "not listening"),
            }),
        )
        dead = probe.run_probe(
            "liveness:\n  - table: brain_index.missing\n",
            runner=FakeRunner({("table", "brain_index.missing"): ("dead", "table missing")}),
        )
        planned = probe.run_probe("")

        self.assertEqual(live.status, "live")
        self.assertEqual(live.event(), "liveness:pass")
        self.assertEqual(partial.status, "partial")
        self.assertEqual(partial.event(), "liveness:partial")
        self.assertEqual(dead.status, "dead")
        self.assertEqual(dead.event(), "liveness:fail")
        self.assertEqual(planned.status, "planned")
        self.assertEqual(planned.event(), "liveness:planned")

    def test_file_probe_is_repo_relative_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "core/STATE").mkdir(parents=True)
            (root / "core/STATE/HOT_STATE.md").write_text("live", encoding="utf-8")
            runner = probe.ProbeRunner(root)

            result = runner.check(probe.LivenessCheck("file", "core/STATE/HOT_STATE.md"))

        self.assertEqual(result.status, "live")
        self.assertEqual(result.detail, "exists")

    def test_ops_ledger_row_carries_honest_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ops.jsonl"
            report = probe.ProbeReport(
                "partial",
                (probe.CheckResult(probe.LivenessCheck("file", "missing"), "dead", "missing"),),
                spec_id="SPEC_d117_demo",
                decision_id="d117",
                branch="build/SPEC_d117_demo",
            )

            self.assertTrue(probe.append_ops_ledger(path, report))

            row = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(row["event"], "liveness:partial")
        self.assertEqual(row["liveness_status"], "partial")
        self.assertIn("Auto-queued activation", row["next"])


if __name__ == "__main__":
    unittest.main()
