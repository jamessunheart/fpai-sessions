import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.liveness import retroactive_audit as audit


class FakeRunner:
    def __init__(self, statuses):
        self.statuses = statuses
        self.checked = []

    def check(self, artifact):
        self.checked.append(artifact)
        return self.statuses.get((artifact.kind, artifact.value), ("unknown", "fixture unknown"))


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if normalized.startswith("insert into brain_index.decisions"):
            decision_id = params[0]
            if decision_id in self.conn.existing:
                self._rows = []
            else:
                self.conn.existing.add(decision_id)
                self.conn.inserted.append(params)
                self._rows = [(decision_id,)]
            return
        raise AssertionError(f"unexpected SQL: {sql}")

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConn:
    def __init__(self, existing=()):
        self.existing = set(existing)
        self.inserted = []
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return FakeCursor(self)


class RetroactiveAuditTest(unittest.TestCase):
    def test_collects_merged_decisions_from_results_in_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "core/BUILD/results").mkdir(parents=True)
            (root / "core/BUILD/activate").mkdir(parents=True)
            (root / "core/BUILD/results/SPEC_d018_live.result.md").write_text("done", encoding="utf-8")
            (root / "core/BUILD/results/SPEC_d093_out.result.md").write_text("done", encoding="utf-8")
            (root / "core/BUILD/activate/SPEC_d054_probe.sh").write_text("#!/bin/sh\n", encoding="utf-8")

            merged = audit.collect_merged_decisions(root, start=1, end=92, ops_ledger=root / "missing.jsonl")

        self.assertEqual(merged, {"d018": "SPEC_d018_live", "d054": "SPEC_d054_probe"})

    def test_infers_activation_systemd_before_repo_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "core/BUILD/specs").mkdir(parents=True)
            (root / "core/BUILD/results").mkdir(parents=True)
            (root / "core/BUILD/activate").mkdir(parents=True)
            (root / "core/BUILD/results/SPEC_d096_scan.result.md").write_text(
                "## Files changed\n- `tools/forge/frontier.py`\n",
                encoding="utf-8",
            )
            (root / "core/BUILD/activate/SPEC_d096_scan.sh").write_text(
                "systemctl enable --now fpai-forge-daily.timer\n",
                encoding="utf-8",
            )

            artifacts = audit.infer_artifacts(root, "d096", "SPEC_d096_scan")

        self.assertEqual(artifacts[0], audit.Artifact("systemd", "fpai-forge-daily.timer", "activation"))
        self.assertIn(audit.Artifact("file", "tools/forge/frontier.py", "result"), artifacts)

    def test_classifies_dead_when_any_concrete_artifact_is_dead(self):
        artifacts = (
            audit.Artifact("file", "tools/live.py", "result"),
            audit.Artifact("systemd", "fpai-live.timer", "activation"),
        )
        runner = FakeRunner({
            ("file", "tools/live.py"): ("live", "exists"),
            ("systemd", "fpai-live.timer"): ("dead", "inactive"),
        })

        status, details = audit.classify(artifacts, runner)

        self.assertEqual(status, "dead")
        self.assertIn("inactive", "\n".join(details))

    def test_render_markdown_uses_three_columns(self):
        row = audit.DecisionAudit(
            "d018",
            "SPEC_d018_live",
            (audit.Artifact("file", "tools/live.py", "result"),),
            "live",
            ("ok",),
        )

        rendered = audit.render_markdown([row])

        self.assertEqual(rendered.splitlines()[0], "| decision | expected artifact | status |")
        self.assertIn("| d018 | file exists: tools/live.py | live |", rendered)

    def test_systemd_inference_ignores_sys_path_but_keeps_units(self):
        text = "Avoid sys.path mutation.\nsystemctl enable --now fpai-live.timer\n"

        self.assertEqual(audit.infer_systemd_units(text), ["fpai-live.timer"])

    def test_systemd_bus_failure_is_unknown_not_dead(self):
        runner = audit.ProbeRunner(Path("."))
        completed = audit.subprocess.CompletedProcess(
            ["systemctl"],
            1,
            stderr="Failed to connect to bus: Operation not permitted",
        )
        with mock.patch.object(audit, "_has_command", return_value=True), mock.patch.object(audit.subprocess, "run", return_value=completed):
            status, detail = runner._check_systemd("fpai-live.timer")

        self.assertEqual(status, "unknown")
        self.assertIn("Failed to connect to bus", detail)

    def test_seed_dead_followups_uses_dnnn_activate_ids(self):
        row = audit.DecisionAudit(
            "d054",
            "SPEC_d054_probe",
            (audit.Artifact("table", "probe_sessions", "spec"),),
            "dead",
            ("table has rows: brain_index.probe_sessions -> dead (0 rows)",),
        )
        conn = FakeConn()
        old_connect = audit.connect
        audit.connect = lambda: conn
        try:
            seeded = audit.seed_dead_followups([row])
        finally:
            audit.connect = old_connect

        self.assertEqual(seeded, ["d054-activate"])
        self.assertEqual(conn.inserted[0][0], "d054-activate")
        self.assertIn("Activate dead merged build d054", conn.inserted[0][1])
        self.assertIn("probe_sessions", conn.inserted[0][3])

    def test_run_audit_writes_report_and_ledger_with_dry_run_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "core/BUILD/results").mkdir(parents=True)
            (root / "core/BUILD/specs").mkdir(parents=True)
            (root / "core/BUILD/activate").mkdir(parents=True)
            (root / "tools/live.py").parent.mkdir(parents=True, exist_ok=True)
            (root / "core/BUILD/results/SPEC_d018_live.result.md").write_text(
                "## Files changed\n- `tools/live.py`\n",
                encoding="utf-8",
            )
            output = root / "liveness_audit.md"
            ledger = root / "ops.jsonl"
            runner = FakeRunner({("file", "tools/live.py"): ("dead", "missing")})

            result = audit.run_audit(
                repo_root=root,
                output=output,
                ops_ledger=ledger,
                seed=True,
                seed_dry_run=True,
                notify=False,
                runner=runner,
            )

            self.assertTrue(output.exists())
            self.assertIn("| d018 | file exists: tools/live.py | dead |", output.read_text(encoding="utf-8"))
            self.assertEqual(result.seeded_decisions, ("d018-activate",))
            self.assertIn('"event": "retroactive_audit"', ledger.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
