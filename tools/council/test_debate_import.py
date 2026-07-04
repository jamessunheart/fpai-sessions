import subprocess
import sys
import textwrap
import unittest


class DebateImportGuardTests(unittest.TestCase):
    def test_debate_import_does_not_load_repo_local_curator_package(self):
        script = textwrap.dedent(
            """
            import importlib.util
            import pathlib
            import sys

            repo = pathlib.Path.cwd().resolve()
            for name in list(sys.modules):
                if name == "curator" or name.startswith("curator."):
                    del sys.modules[name]

            spec = importlib.util.spec_from_file_location("debate_import_guard", repo / "tools/council/debate.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            curator = sys.modules.get("curator")
            if curator is not None:
                curator_file = pathlib.Path(getattr(curator, "__file__", "")).resolve()
                if curator_file == repo / "curator/__init__.py":
                    raise SystemExit(f"repo-local curator package loaded: {curator_file}")
            print("ok")
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=__import__("pathlib").Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
