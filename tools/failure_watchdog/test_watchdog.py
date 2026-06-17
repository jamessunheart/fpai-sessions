from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tools.failure_watchdog import watchdog


class FailureWatchdogTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp())
        for rel in (
            "docs/codex",
            "core/BUILD/signals",
            "core/BUILD/results",
            "tools/results",
            "SERVICES/api",
            "SERVICES/web",
            "scripts",
        ):
            (root / rel).mkdir(parents=True, exist_ok=True)
        (root / "docs/codex/AI_PROTOCOLS.md").write_text("doctrine", encoding="utf-8")
        (root / "docs/codex/HANDOFF.md").write_text("handoff", encoding="utf-8")
        (root / "docs/codex/INDEX_OF_INDEXES.md").write_text("index", encoding="utf-8")
        (root / "docs/codex/HOST_REGISTRY.md").write_text("Live heartbeat coverage | none yet\n", encoding="utf-8")
        (root / "docs/codex/SUBSCRIPTION_DEPENDENCY_MAP.md").write_text("Claude Max Pulled\n", encoding="utf-8")
        (root / "core/BUILD/signals/agent_scoring_ledger.jsonl").write_text('{"agent_id":"codex"}\n', encoding="utf-8")
        (root / "core/BUILD/REGISTRY.json").write_text(
            json.dumps({"active_builds": [{"id": "d060", "status": "building"}]}),
            encoding="utf-8",
        )
        (root / "tools/results/engine.py").write_text("next: Name 3-5 warm leads\ntier: human\n", encoding="utf-8")
        return root

    def test_detects_spofs_across_required_categories(self) -> None:
        root = self.make_repo()
        (root / "scripts/activate-revenue-streams.sh").write_text("curl http://198.54.123.234:8600/health\n", encoding="utf-8")
        (root / "SERVICES/api/requirements.txt").write_text("fastapi==0.100.0\nuvicorn\n", encoding="utf-8")
        (root / "SERVICES/web/requirements.txt").write_text("fastapi==0.111.0\nuvicorn\n", encoding="utf-8")
        (root / "SERVICES/web/package.json").write_text(
            json.dumps({"dependencies": {"@fpai/client": "^1.2.0", "solid-js": "1.8.0"}}),
            encoding="utf-8",
        )
        (root / "SERVICES/api/pyproject.toml").write_text(
            '[project]\ndependencies = ["httpx", "pydantic==2.6.4"]\n',
            encoding="utf-8",
        )
        now = datetime(2026, 6, 16, 12, tzinfo=timezone.utc)
        ledger = root / "ops.jsonl"
        ledger.write_text(
            json.dumps({
                "ts": (now - timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "loop": "smoke_test",
                "event": "smoke_pass",
                "status": "PASS",
            }) + "\n",
            encoding="utf-8",
        )

        report = watchdog.run(
            repo_root=root,
            json_path=root / "out.json",
            markdown_path=root / "out.md",
            ops_ledger=ledger,
            disable_file=root / ".disabled",
            cooldown_file=root / ".cooldown",
            now=now,
            no_ledger=True,
        )

        categories = {finding["category"] for finding in report["findings"]}
        self.assertTrue({"server", "memory", "revenue", "dependencies"}.issubset(categories))
        titles = "\n".join(finding["title"] for finding in report["findings"])
        self.assertIn("Direct host/IP dependencies", titles)
        self.assertIn("Smoke-test proof is stale", titles)
        self.assertIn("Conflicting pinned dependency versions", titles)
        self.assertEqual(watchdog.package_json_dependencies(root / "SERVICES/web/package.json")["@fpai/client"], "^1.2.0")
        self.assertIn("httpx", watchdog.pyproject_dependencies(root / "SERVICES/api/pyproject.toml"))
        self.assertTrue((root / "out.json").exists())
        self.assertIn("Proactive Failure Watchdog Report", (root / "out.md").read_text(encoding="utf-8"))

    def test_public_ipv4_detection_is_not_two_ip_allowlist(self) -> None:
        root = self.make_repo()
        (root / "tools/fleet_state.py").write_text("PRIMARY = 'http://209.74.93.72:8080/health'\n", encoding="utf-8")
        report = watchdog.run(
            repo_root=root,
            json_path=root / "out.json",
            markdown_path=root / "out.md",
            ops_ledger=root / "ops.jsonl",
            disable_file=root / ".disabled",
            cooldown_file=root / ".cooldown",
            no_ledger=True,
        )
        self.assertIn("209.74.93.72:8080", json.dumps(report["findings"]))

    def test_missing_core_memory_is_p0(self) -> None:
        root = self.make_repo()
        (root / "docs/codex/AI_PROTOCOLS.md").unlink()
        report = watchdog.run(
            repo_root=root,
            json_path=root / "out.json",
            markdown_path=root / "out.md",
            ops_ledger=root / "ops.jsonl",
            disable_file=root / ".disabled",
            cooldown_file=root / ".cooldown",
            no_ledger=True,
        )
        self.assertGreaterEqual(report["summary"]["p0"], 1)
        self.assertIn("Core memory mirror files are missing", [f["title"] for f in report["findings"]])

    def test_disabled_run_does_not_write_reports_or_ledger(self) -> None:
        root = self.make_repo()
        disable = root / ".disabled"
        disable.write_text("off", encoding="utf-8")
        report = watchdog.run(
            repo_root=root,
            json_path=root / "out.json",
            markdown_path=root / "out.md",
            ops_ledger=root / "ops.jsonl",
            disable_file=disable,
            cooldown_file=root / ".cooldown",
        )
        self.assertTrue(report["disabled"])
        self.assertFalse((root / "out.json").exists())
        self.assertFalse((root / "ops.jsonl").exists())

    def test_ledger_row_written_for_normal_run(self) -> None:
        root = self.make_repo()
        ledger = root / "ops.jsonl"
        report = watchdog.run(
            repo_root=root,
            json_path=root / "out.json",
            markdown_path=root / "out.md",
            ops_ledger=ledger,
            disable_file=root / ".disabled",
            cooldown_file=root / ".cooldown",
        )
        self.assertTrue(report["ledger_written"])
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[-1]["loop"], "failure_watchdog")
        self.assertIn(rows[-1]["event"], {"ran", "proposed", "failed"})

    def test_alert_cooldown_threshold(self) -> None:
        now = datetime(2026, 6, 16, 12, tzinfo=timezone.utc)
        report = {
            "summary": {"max_severity": 4},
            "findings": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            cooldown = Path(tmp) / "cooldown"
            self.assertTrue(watchdog.should_alert(report, cooldown, now))
            cooldown.write_text((now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), encoding="utf-8")
            self.assertFalse(watchdog.should_alert(report, cooldown, now))

    def test_send_alert_requires_actual_sent_output(self) -> None:
        root = self.make_repo()
        (root / "tools/build_loop").mkdir(parents=True, exist_ok=True)
        (root / "tools/build_loop/notify_telegram.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        skipped = mock.Mock(returncode=0, stdout="notify: no creds at /x (skipped)", stderr="")
        sent = mock.Mock(returncode=0, stdout="notify: sent to 123", stderr="")
        with mock.patch("tools.failure_watchdog.watchdog.subprocess.run", return_value=skipped):
            self.assertFalse(watchdog.send_alert(root, "msg"))
        with mock.patch("tools.failure_watchdog.watchdog.subprocess.run", return_value=sent):
            self.assertTrue(watchdog.send_alert(root, "msg"))


if __name__ == "__main__":
    unittest.main()
