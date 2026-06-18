import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.inventory import scan_resources


class ResourceInventoryTest(unittest.TestCase):
    def test_configured_apis_filters_secret_shaped_names(self):
        env = {
            "TWILIO_ACCOUNT_SID": "AC123",
            "STRIPE_SECRET_KEY": "secret",
            "OPENAI_API_KEY": "secret",
            "BREVO_REGION": "eu",
            "PATH": "/usr/bin",
        }

        names = scan_resources.collect_configured_apis(env)

        self.assertEqual(names, ["BREVO_REGION", "TWILIO_ACCOUNT_SID"])

    def test_collect_local_scripts_skips_dependency_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "ignored.py").write_text("print('x')\n", encoding="utf-8")

            scripts = scan_resources.collect_local_scripts(root)

        self.assertEqual(scripts, ["scripts/run.sh"])

    def test_render_inventory_has_required_sections_and_no_values(self):
        content = scan_resources.render_inventory(
            generated_at="2026-06-18T00:00:00Z",
            clis=[("git", "/usr/bin/git"), ("stripe", None)],
            python_libs=[("requests", "2.32.0")],
            configured_apis=["TWILIO_ACCOUNT_SID"],
            local_scripts=["scripts/run.sh"],
            script_root=Path("/opt/fpai"),
        )

        self.assertIn("## CLIs", content)
        self.assertIn("## Python-libs", content)
        self.assertIn("## Configured-APIs", content)
        self.assertIn("## Local-scripts", content)
        self.assertIn("- git: /usr/bin/git", content)
        self.assertIn("- stripe: not found", content)
        self.assertIn("- requests==2.32.0", content)
        self.assertIn("- TWILIO_ACCOUNT_SID", content)
        self.assertNotIn("AC123", content)

    def test_collect_clis_uses_shutil_which(self):
        def fake_which(name):
            return "/usr/bin/git" if name == "git" else None

        with mock.patch.object(scan_resources.shutil, "which", side_effect=fake_which):
            clis = dict(scan_resources.collect_clis(["git", "curl"]))

        self.assertEqual(clis["git"], "/usr/bin/git")
        self.assertIsNone(clis["curl"])

    def test_read_inventory_context_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AVAILABLE_RESOURCES.md"
            path.write_text("# Available Resources\n" + ("x" * 80), encoding="utf-8")

            text = scan_resources.read_inventory_context(path, limit=40)

        self.assertIn("# Available Resources", text)
        self.assertIn("truncated to 40 chars", text)


if __name__ == "__main__":
    unittest.main()
