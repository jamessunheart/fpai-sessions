from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.infra import stop_cruft_services_198 as cruft


class StopCruftServices198Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        snapshot = self.root / "core" / "STATE" / "FLEET_SNAPSHOT.md"
        snapshot.parent.mkdir(parents=True)
        snapshot.write_text(
            "- Uptime 150d; disk 23%; RAM: 1.27G free of 7.9G, swap 2.8G/4G used\n"
            "- 198 swap still heavy: cruft services (cocoon, whaletrack-magnet?) per NOW.md cruft-watch\n",
            encoding="utf-8",
        )
        self.ledger = self.root / "ops_ledger.jsonl"
        self.meminfo = self.root / "meminfo"
        self.meminfo.write_text(
            "MemTotal: 8000000 kB\n"
            "MemFree: 500000 kB\n"
            "MemAvailable: 1000000 kB\n"
            "SwapTotal: 4000000 kB\n"
            "SwapFree: 1200000 kB\n",
            encoding="utf-8",
        )
        self.fake_systemctl = self.root / "systemctl"
        self.calls = self.root / "systemctl.calls"
        self.marker = self.root / "disabled.marker"
        self.fake_systemctl.write_text(
            "#!/usr/bin/env bash\n"
            "echo \"$*\" >> \"$SYSTEMCTL_CALLS\"\n"
            "case \"$1\" in\n"
            "  is-active)\n"
            "    if [ -e \"$DISABLED_MARKER\" ]; then echo inactive; else echo active; fi ;;\n"
            "  is-enabled)\n"
            "    if [ -e \"$DISABLED_MARKER\" ]; then echo disabled; else echo enabled; fi ;;\n"
            "  disable)\n"
            "    touch \"$DISABLED_MARKER\"\n"
            "    cat > \"$FPAI_D146_MEMINFO\" <<'EOF'\n"
            "MemTotal: 8000000 kB\n"
            "MemFree: 900000 kB\n"
            "MemAvailable: 1650000 kB\n"
            "SwapTotal: 4000000 kB\n"
            "SwapFree: 1800000 kB\n"
            "EOF\n"
            "    exit 0 ;;\n"
            "  *) exit 3 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        self.fake_systemctl.chmod(self.fake_systemctl.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _env(self, **extra: str):
        values = {
            "SYSTEMCTL": str(self.fake_systemctl),
            "SYSTEMCTL_CALLS": str(self.calls),
            "DISABLED_MARKER": str(self.marker),
            "FPAI_D146_MEMINFO": str(self.meminfo),
            "FPAI_D146_HOST_IPS": cruft.TARGET_IP,
        }
        values.update(extra)
        return mock.patch.dict(os.environ, values, clear=False)

    def test_execute_on_target_requires_flag_then_stops_and_logs_ram(self) -> None:
        with self._env(FPAI_D146_CRUFT_STOP="1"):
            row = cruft.run(
                self.root,
                self.ledger,
                execute=True,
                record=True,
                settle_seconds=0,
            )

        self.assertEqual(row["event"], "succeeded")
        self.assertEqual(row["ram_reclaimed_kib"], 650000)
        self.assertEqual(row["after"]["fpai-cocoon.service"]["active"], "inactive")
        self.assertEqual(row["after"]["whaletrack-magnet.service"]["enabled"], "disabled")
        self.assertIn(
            "disable --now fpai-cocoon.service whaletrack-magnet.service",
            self.calls.read_text(encoding="utf-8"),
        )
        rows = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["spec_id"], cruft.SPEC_ID)
        self.assertEqual(rows[0]["rollback"], cruft.ROLLBACK)
        self.assertEqual(rows[0]["ram_reclaimed_kib"], 650000)

    def test_execute_on_target_without_flag_records_no_action(self) -> None:
        with self._env(FPAI_D146_CRUFT_STOP="0"):
            row = cruft.run(
                self.root,
                self.ledger,
                execute=True,
                record=True,
                settle_seconds=0,
            )

        self.assertEqual(row["event"], "flag_disabled")
        self.assertFalse(self.marker.exists())
        self.assertNotIn("disable --now", self.calls.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["event"], "flag_disabled")

    def test_execute_off_target_skips_without_systemctl_or_memory_probe(self) -> None:
        with self._env(FPAI_D146_HOST_IPS="10.0.0.5", FPAI_D146_CRUFT_STOP="1"):
            row = cruft.run(
                self.root,
                self.ledger,
                execute=True,
                record=True,
                settle_seconds=0,
            )

        self.assertEqual(row["event"], "skipped")
        self.assertFalse(self.calls.exists())
        rows = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["host_target"], cruft.TARGET_IP)

    def test_missing_fleet_evidence_blocks_service_change(self) -> None:
        (self.root / "core" / "STATE" / "FLEET_SNAPSHOT.md").write_text(
            "- 198 RAM healthy; no named cruft here\n",
            encoding="utf-8",
        )
        with self._env(FPAI_D146_CRUFT_STOP="1"), self.assertRaises(cruft.CruftStopError):
            cruft.run(
                self.root,
                self.ledger,
                execute=True,
                record=True,
                settle_seconds=0,
            )

        self.assertFalse(self.calls.exists())
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
