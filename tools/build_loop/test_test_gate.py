#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_loop import test_gate


class BuildLoopPytestGateTests(unittest.TestCase):
    def make_repo(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        return root

    def test_selects_touched_tests_adjacent_module_tests_and_smoke_subset(self) -> None:
        root = self.make_repo()
        files = {
            "tools/demo/thing.py": "def value():\n    return 1\n",
            "tools/demo/test_thing.py": "def test_value():\n    assert True\n",
            "tools/build_loop/server_build_loop.sh": "#!/usr/bin/env bash\n",
            "tools/build_loop/test_auto_merge_governance.py": "def test_smoke():\n    assert True\n",
            "tools/other/test_new.py": "def test_new():\n    assert True\n",
        }
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        changed = ["tools/demo/thing.py", "tools/other/test_new.py", "tools/build_loop/server_build_loop.sh"]
        selection = test_gate.select_tests(
            root,
            changed,
            smoke_subset=("tools/build_loop/test_auto_merge_governance.py",),
        )

        self.assertIn("tools/demo/test_thing.py", selection["adjacent_tests"])
        self.assertIn("tools/other/test_new.py", selection["touched_tests"])
        self.assertIn("tools/build_loop/test_auto_merge_governance.py", selection["smoke_tests"])
        self.assertEqual(
            selection["selected_tests"],
            [
                "tools/other/test_new.py",
                "tools/demo/test_thing.py",
                "tools/build_loop/test_auto_merge_governance.py",
            ],
        )

    def test_pytest_failure_returns_failed_report_and_nonzero_main(self) -> None:
        root = self.make_repo()
        (root / "pytest.py").write_text(
            "import sys\nprint('1 failed, 2 passed in 0.01s')\nsys.exit(1)\n",
            encoding="utf-8",
        )
        test_file = root / "test_fail.py"
        test_file.write_text("def test_fail():\n    assert True\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)
        subprocess.run(["git", "checkout", "-q", "-b", "build/demo"], cwd=root, check=True)
        test_file.write_text("def test_fail():\n    assert False\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "break test"], cwd=root, check=True)
        report_path = root / "core/BUILD/reports/SPEC_demo.test_gate.json"

        with redirect_stdout(StringIO()):
            code = test_gate.main(
                [
                    "--repo-root",
                    str(root),
                    "--base-ref",
                    "master",
                    "--head-ref",
                    "HEAD",
                    "--spec-id",
                    "SPEC_demo",
                    "--python",
                    sys.executable,
                    "--timeout",
                    "30",
                    "--output",
                    str(report_path),
                ]
            )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["counts"]["failed"], 1)
        self.assertIn("test_fail.py", report["selected_tests"])
        self.assertIn("-x", report["command"])

    def test_timeout_report_is_failure(self) -> None:
        root = self.make_repo()
        (root / "pytest.py").write_text(
            "import time\ntime.sleep(5)\n",
            encoding="utf-8",
        )
        slow_test = root / "test_slow.py"
        slow_test.write_text(
            textwrap.dedent(
                """\
                import time
                def test_slow():
                    time.sleep(5)
                """
            ),
            encoding="utf-8",
        )
        result = test_gate.run_pytest(
            repo_root=root,
            pytest_python=sys.executable,
            selected_tests=[str(slow_test)],
            timeout_seconds=1,
        )

        self.assertEqual(result["status"], "timed_out")
        self.assertEqual(result["returncode"], 124)


if __name__ == "__main__":
    unittest.main()
