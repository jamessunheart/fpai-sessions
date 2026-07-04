from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.build_loop import live_service_guard as guard


def completed(args: list[str], rc: int = 0, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, rc, stdout=out, stderr=err)


class LiveServiceGuardTest(unittest.TestCase):
    def test_detects_bot_target_from_changed_files(self) -> None:
        targets = guard.detect_targets(["SERVICES/sunheart-brain/curator/tgbot.py"])
        self.assertEqual(["sunheart-brain-tgbot"], [target.name for target in targets])

    def test_backup_and_restore_live_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live = root / "sh-brain-src"
            file_path = live / "curator" / "tgbot.py"
            file_path.parent.mkdir(parents=True)
            file_path.write_text("old bot\n", encoding="utf-8")
            backup_root = root / "backups"
            target = guard.TARGETS[0]

            with mock.patch.dict(os.environ, {"SH_BRAIN_SRC": str(live)}):
                backup = guard.create_backup([target], backup_root, "SPEC_d182_x")
                file_path.write_text("broken bot\n", encoding="utf-8")
                guard.restore_backup(backup, [target], runner=lambda *a, **k: completed(a[0]))

            self.assertEqual("old bot\n", file_path.read_text(encoding="utf-8"))

    def test_smoke_failure_restores_backup_and_sends_one_line_alert(self) -> None:
        commands: list[list[str]] = []

        def fake_runner(args, **kwargs):
            commands.append(list(args))
            if args[:3] == ["git", "-C", str(repo)]:
                return completed(args, out="SERVICES/sunheart-brain/curator/tgbot.py\n")
            if args[:1] == ["bash"] and str(args[1]).endswith("activate.sh"):
                live_file.write_text("broken bot\n", encoding="utf-8")
                return completed(args)
            if args[:3] == ["systemctl", "is-active", "--quiet"]:
                return completed(args, rc=1, err="inactive")
            return completed(args)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            notify = repo / "tools" / "build_loop" / "notify_telegram.sh"
            notify.parent.mkdir(parents=True)
            notify.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            activate = repo / "activate.sh"
            activate.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            live = root / "sh-brain-src"
            live_file = live / "curator" / "tgbot.py"
            live_file.parent.mkdir(parents=True)
            live_file.write_text("old bot\n", encoding="utf-8")
            args = argparse.Namespace(
                repo_root=str(repo),
                spec_id="SPEC_d182_x",
                decision_id="d182",
                branch="build/SPEC_d182_x",
                activate_script=str(activate),
                base_ref="before",
                head_ref="after",
                backup_root=str(root / "backups"),
                ops_ledger=str(root / "ops.jsonl"),
                activate_timeout="20",
            )
            with mock.patch.dict(os.environ, {"SH_BRAIN_SRC": str(live)}):
                result = guard.activate_with_guard(args, runner=fake_runner)
                restored = live_file.read_text(encoding="utf-8")

            self.assertFalse(result.ok)
            self.assertEqual("old bot\n", restored)
        alert_commands = [cmd for cmd in commands if cmd[:1] == ["bash"] and str(cmd[1]).endswith("notify_telegram.sh")]
        self.assertEqual(1, len(alert_commands))
        self.assertIn("d182 deploy failed smoke-test, auto-reverted:", alert_commands[0][2])
        self.assertIn("sh-brain-tgbot.service is not active", alert_commands[0][2])


if __name__ == "__main__":
    unittest.main()
