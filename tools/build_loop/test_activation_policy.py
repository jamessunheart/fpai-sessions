#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.build_loop import activation_policy


class ActivationPolicyTests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-activation-policy-"))
        (root / "core" / "BUILD" / "activate").mkdir(parents=True)
        (root / "core" / "BUILD" / "specs").mkdir(parents=True)
        (root / "core" / "BUILD" / "results").mkdir(parents=True)
        return root

    def test_activation_script_satisfies_policy(self) -> None:
        root = self.make_repo()
        (root / "core" / "BUILD" / "activate" / "SPEC_d001_demo.sh").write_text("#!/usr/bin/env bash\n")

        result = activation_policy.check_policy(root, spec_id="SPEC_d001_demo")

        self.assertTrue(result.ok)
        self.assertEqual(result.activation_script, "core/BUILD/activate/SPEC_d001_demo.sh")

    def test_library_declaration_satisfies_policy(self) -> None:
        root = self.make_repo()
        (root / "core" / "BUILD" / "results" / "SPEC_d002_lib.result.md").write_text(
            "build_kind=library\n",
            encoding="utf-8",
        )

        result = activation_policy.check_policy(root, spec_id="SPEC_d002_lib")

        self.assertTrue(result.ok)
        self.assertEqual(result.build_kind, "library")

    def test_changed_build_without_activation_or_declaration_fails(self) -> None:
        root = self.make_repo()
        with patch.object(activation_policy, "changed_files", return_value=["tools/new_capability.py"]):
            result = activation_policy.check_policy(root, spec_id="SPEC_d003_missing")

        self.assertFalse(result.ok)
        self.assertIn("activate", result.reason)
        self.assertIn("build_kind=library/inert", result.reason)

    def test_no_changed_files_is_non_blocking(self) -> None:
        root = self.make_repo()
        with patch.object(activation_policy, "changed_files", return_value=[]):
            result = activation_policy.check_policy(root, spec_id="SPEC_d004_empty")

        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
