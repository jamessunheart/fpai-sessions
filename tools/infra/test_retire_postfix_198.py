from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.infra import retire_postfix_198 as retire


class RetirePostfix198Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        inventory = self.root / "core" / "STATE" / "RESOURCE_INVENTORY.md"
        inventory.parent.mkdir(parents=True)
        inventory.write_text(
            "| Email | live | sunheartai@fullpotential.ai | Sends via Brevo |\n"
            "| Brevo (email) | live | curator.env -> BREVO_API_KEY | Sends from sunheartai@fullpotential.ai |\n",
            encoding="utf-8",
        )
        self.ledger = self.root / "ops_ledger.jsonl"
        self.fake_systemctl = self.root / "systemctl"
        self.calls = self.root / "systemctl.calls"
        self.fake_systemctl.write_text(
            "#!/usr/bin/env bash\n"
            "echo \"$*\" >> \"$SYSTEMCTL_CALLS\"\n"
            "case \"$1\" in\n"
            "  is-active) echo active ;;\n"
            "  is-enabled) echo enabled ;;\n"
            "  disable) exit 0 ;;\n"
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
            "FPAI_POSTFIX_RETIRE_HOST_IPS": retire.TARGET_IP,
        }
        values.update(extra)
        return mock.patch.dict(os.environ, values, clear=False)

    def test_execute_on_target_disables_postfix_and_logs_rollback(self) -> None:
        with self._env():
            row = retire.run(self.root, self.ledger, execute=True)

        self.assertEqual(row["event"], "succeeded")
        self.assertEqual(row["rollback"], "systemctl enable --now postfix")
        self.assertIn(retire.TARGET_IP, row["local_ips"])
        self.assertIn("disable --now postfix", self.calls.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["spec_id"], retire.SPEC_ID)
        self.assertEqual(rows[0]["decision_id"], "d145")
        self.assertEqual(rows[0]["service"], "postfix")

    def test_execute_off_target_skips_without_systemctl_action(self) -> None:
        with self._env(FPAI_POSTFIX_RETIRE_HOST_IPS="10.0.0.5"):
            row = retire.run(self.root, self.ledger, execute=True)

        self.assertEqual(row["event"], "skipped")
        self.assertFalse(self.calls.exists())
        rows = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["event"], "skipped")
        self.assertEqual(rows[0]["host_target"], retire.TARGET_IP)

    def test_missing_brevo_evidence_blocks_service_change(self) -> None:
        (self.root / "core" / "STATE" / "RESOURCE_INVENTORY.md").write_text(
            "| Email | live | local SMTP only |\n",
            encoding="utf-8",
        )
        with self._env(), self.assertRaises(retire.RetireError):
            retire.run(self.root, self.ledger, execute=True)

        self.assertFalse(self.calls.exists())
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
