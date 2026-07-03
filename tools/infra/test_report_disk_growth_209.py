from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.infra import report_disk_growth_209 as disk209


class DiskGrowth209Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        snapshot = self.root / "core" / "STATE" / "FLEET_SNAPSHOT.md"
        snapshot.parent.mkdir(parents=True)
        snapshot.write_text(
            "## 209.74.93.72 - server1.outbounders.com - cPanel/WHM\n"
            "- Uptime 404d - disk 70% (1.2T/1.8T - up from 67% on 06-12, watch trend)\n"
            "- 209 disk trend: identify top growth dirs before it becomes urgent\n",
            encoding="utf-8",
        )
        self.previous = self.root / "previous.json"
        self.snapshot_out = self.root / "snapshot.json"
        self.report_json = self.root / "report.json"
        self.report_md = self.root / "report.md"
        self.ledger = self.root / "ledger.jsonl"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _runner(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        if cmd[:3] == ["df", "-B1", "-P"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                "Filesystem 1B-blocks Used Available Use% Mounted on\n"
                "/dev/sda1 1800000000000 1260000000000 540000000000 70% /\n",
                "",
            )
        if cmd[0] == "du" and cmd[-1] == "/home":
            return subprocess.CompletedProcess(
                cmd,
                0,
                "900000000000\t/home\n"
                "300000000000\t/home/acct1\n"
                "90000000000\t/home/acct1/logs\n"
                "120000000000\t/home/acct2/mail\n",
                "",
            )
        if cmd[0] == "du" and cmd[-1] == "/backup":
            return subprocess.CompletedProcess(
                cmd,
                0,
                "450000000000\t/backup\n"
                "200000000000\t/backup/monthly\n",
                "",
            )
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def _run(self, **extra):
        kwargs = {
            "roots": ("/home", "/backup"),
            "depth": 2,
            "previous_snapshot": self.previous,
            "snapshot_out": self.snapshot_out,
            "report_json": self.report_json,
            "report_md": self.report_md,
            "ledger": self.ledger,
            "record": True,
            "require_target": True,
            "runner": self._runner,
        }
        kwargs.update(extra)
        with mock.patch.dict(os.environ, {"FPAI_D147_HOST_IPS": disk209.TARGET_IP}, clear=False):
            return disk209.run(self.root, **kwargs)

    def test_report_computes_growth_and_writes_reversible_proposals(self) -> None:
        self.previous.write_text(
            json.dumps(
                {
                    "dirs": [
                        {"path": "/home/acct1/logs", "size_bytes": 50000000000},
                        {"path": "/backup/monthly", "size_bytes": 180000000000},
                    ]
                }
            ),
            encoding="utf-8",
        )

        report = self._run()

        self.assertEqual(report["event"], "reported")
        self.assertTrue(report["previous_snapshot_loaded"])
        paths = [row["path"] for row in report["top_growth_dirs"][:3]]
        self.assertIn("/home", paths)
        logs_row = next(row for row in report["top_growth_dirs"] if row["path"] == "/home/acct1/logs")
        self.assertEqual(logs_row["growth_bytes"], 40000000000)
        proposals = {item["path"]: item for item in report["cleanup_proposals"]}
        self.assertIn("quarantine", proposals["/home/acct1/logs"]["proposed_action"].lower())
        self.assertIn("Rollback", self.report_md.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["spec_id"], disk209.SPEC_ID)

    def test_missing_previous_snapshot_seeds_baseline_and_marks_new_paths(self) -> None:
        report = self._run()

        self.assertFalse(report["previous_snapshot_loaded"])
        self.assertTrue(report["top_growth_dirs"][0]["new_path"])
        self.assertTrue(self.snapshot_out.exists())
        self.assertTrue(self.report_json.exists())

    def test_off_target_skips_without_running_df_or_du(self) -> None:
        calls: list[list[str]] = []

        def runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with mock.patch.dict(os.environ, {"FPAI_D147_HOST_IPS": "10.0.0.5"}, clear=False):
            row = disk209.run(
                self.root,
                roots=("/home",),
                depth=1,
                previous_snapshot=self.previous,
                snapshot_out=self.snapshot_out,
                report_json=self.report_json,
                report_md=self.report_md,
                ledger=self.ledger,
                record=True,
                require_target=True,
                runner=runner,
            )

        self.assertEqual(row["event"], "skipped")
        self.assertEqual(calls, [])
        self.assertFalse(self.report_json.exists())
        rows = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["host_target"], disk209.TARGET_IP)

    def test_missing_fleet_evidence_blocks_report(self) -> None:
        (self.root / "core" / "STATE" / "FLEET_SNAPSHOT.md").write_text(
            "- server healthy; no trend here\n",
            encoding="utf-8",
        )

        with self.assertRaises(disk209.DiskReportError):
            self._run()


if __name__ == "__main__":
    unittest.main()
