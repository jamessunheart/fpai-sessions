import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE = Path(__file__).with_name("mirror_pull.py")
SPEC = importlib.util.spec_from_file_location("mirror_pull", MODULE)
mirror_pull = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mirror_pull)


class MirrorPullVaultPathTests(unittest.TestCase):
    def test_write_vault_text_falls_back_when_first_candidate_is_permission_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blocked = root / "icloud" / "Full Potential OS"
            fallback = root / "Documents" / "FPOS" / "Full Potential OS"
            original_mkdir = Path.mkdir

            def mkdir_with_tcc_denial(path, *args, **kwargs):
                if str(path).startswith(str(blocked)):
                    raise PermissionError("Operation not permitted")
                return original_mkdir(path, *args, **kwargs)

            with mock.patch.object(Path, "mkdir", mkdir_with_tcc_denial):
                written = mirror_pull.write_vault_text(
                    "02_CONTEXT/Memory/BRAIN DIGEST.md",
                    "digest",
                    [blocked, fallback],
                )

            self.assertEqual(written, fallback / "02_CONTEXT/Memory" / "BRAIN DIGEST.md")
            self.assertEqual(written.read_text(), "digest")

    def test_write_vault_text_raises_when_all_candidates_are_permission_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocked = Path(tmp) / "icloud" / "Full Potential OS"

            with mock.patch.object(Path, "mkdir", side_effect=PermissionError("Operation not permitted")):
                with self.assertRaises(PermissionError) as ctx:
                    mirror_pull.write_vault_text(
                        "02_CONTEXT/Memory/BRAIN DIGEST.md",
                        "digest",
                        [blocked],
                    )

            self.assertIn("could not write vault mirror", str(ctx.exception))
            self.assertIn("Operation not permitted", str(ctx.exception))

    def test_choose_vault_prefers_first_existing_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "Documents" / "FPOS" / "Full Potential OS"
            icloud = root / "Documents" / "FPOS" / "Full Potential OS"
            local.mkdir(parents=True)
            icloud.mkdir(parents=True)

            self.assertEqual(mirror_pull.choose_vault([local, icloud]), local)


if __name__ == "__main__":
    unittest.main()
