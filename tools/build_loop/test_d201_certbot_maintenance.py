#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "core" / "BUILD" / "activate" / "SPEC_d201_infra-certbot-pyopenssl-cryptog.sh"


class D201CertbotMaintenanceTests(unittest.TestCase):
    def run_script(self, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        base_env = {
            "PATH": os.environ.get("PATH", ""),
            "D201_LOG_DIR": self.tmp.name,
            "D201_BACKUP_ROOT": str(Path(self.tmp.name) / "backups"),
            "D201_DISABLE_FILE": str(Path(self.tmp.name) / "disabled"),
        }
        base_env.update(env)
        return subprocess.run(
            ["bash", str(SCRIPT)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=base_env,
            check=False,
            timeout=10,
        )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="fpai-d201-certbot-")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_without_maintenance_approval_holds_without_mutation(self) -> None:
        result = self.run_script({})

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("hold: set D201_CERTBOT_MAINTENANCE_APPROVED=1", result.stdout)
        self.assertIn("no package changes were made", result.stdout)
        self.assertNotIn("renew --dry-run", result.stdout)

    def test_approved_run_requires_explicit_strategy(self) -> None:
        fake_certbot = Path(self.tmp.name) / "certbot"
        fake_certbot.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        fake_certbot.chmod(0o755)

        result = self.run_script(
            {
                "D201_CERTBOT_MAINTENANCE_APPROVED": "1",
                "D201_ALLOW_NON_162": "1",
                "CERTBOT_BIN": str(fake_certbot),
            }
        )

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("set D201_CERTBOT_STRATEGY", result.stdout)

    def test_dry_run_venv_strategy_prints_fix_and_proof_commands(self) -> None:
        fake_python = Path(self.tmp.name) / "venv" / "bin" / "python"
        fake_python.parent.mkdir(parents=True)
        fake_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_python.chmod(0o755)

        fake_certbot = Path(self.tmp.name) / "certbot"
        fake_certbot.write_text(f"#!{fake_python}\n", encoding="utf-8")
        fake_certbot.chmod(0o755)

        result = self.run_script(
            {
                "D201_CERTBOT_MAINTENANCE_APPROVED": "1",
                "D201_ALLOW_NON_162": "1",
                "D201_CERTBOT_STRATEGY": "venv-upgrade",
                "D201_DRY_RUN": "1",
                "CERTBOT_BIN": str(fake_certbot),
                "SYSTEMCTL": "systemctl",
            }
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("-m pip install --upgrade pyOpenSSL>=24.0.0 cryptography>=41,<46", result.stdout)
        self.assertIn("renew --dry-run", result.stdout)
        self.assertIn("start certbot.service", result.stdout)
        self.assertIn("is-active certbot.timer", result.stdout)
        self.assertIn("proof complete", result.stdout)

    def test_system_pip_strategy_needs_second_explicit_gate(self) -> None:
        fake_certbot = Path(self.tmp.name) / "certbot"
        fake_certbot.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        fake_certbot.chmod(0o755)

        result = self.run_script(
            {
                "D201_CERTBOT_MAINTENANCE_APPROVED": "1",
                "D201_ALLOW_NON_162": "1",
                "D201_CERTBOT_STRATEGY": "system-pip-upgrade",
                "CERTBOT_BIN": str(fake_certbot),
            }
        )

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("system-pip-upgrade requires D201_ALLOW_SYSTEM_PIP=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
