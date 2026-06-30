from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.constitution import surface


class ConstitutionSurfaceTest(unittest.TestCase):
    def test_resolve_source_prefers_mirror_constitution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "core" / "INTENT" / "AGREEMENTS" / "CONSTITUTION_v1.md"
            fallback = root / "core" / "knowledge" / "CONSTITUTION.md"
            primary.parent.mkdir(parents=True)
            fallback.parent.mkdir(parents=True)
            primary.write_text("# Mirror Constitution\n\nprimary", encoding="utf-8")
            fallback.write_text("# Full Potential Constitution\n\nfallback", encoding="utf-8")

            resolved = surface.resolve_source(repo_root=root)

        self.assertEqual(resolved.relative_path, "core/INTENT/AGREEMENTS/CONSTITUTION_v1.md")
        self.assertEqual(resolved.title, "Mirror Constitution")
        self.assertIn("primary", resolved.text)

    def test_source_override_is_used_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            override = root / "custom.md"
            override.write_text("# Governance\n\nchosen", encoding="utf-8")

            resolved = surface.resolve_source(repo_root=root, source="custom.md")

        self.assertEqual(resolved.relative_path, "custom.md")
        self.assertEqual(resolved.title, "Governance")

    def test_telegram_messages_escape_html_and_chunk(self) -> None:
        source = surface.ConstitutionSource(
            path=Path("/repo/core/knowledge/CONSTITUTION.md"),
            relative_path="core/knowledge/CONSTITUTION.md",
            title="Full <Potential>",
            text="# Full <Potential>\n\nA & B\n\n" + ("x" * 1200),
        )

        messages = surface.telegram_messages(source, limit=900)

        self.assertGreater(len(messages), 1)
        self.assertIn("Full &lt;Potential&gt;", messages[0])
        self.assertIn("A &amp; B", messages[0])
        self.assertTrue(all(len(message) <= 1400 for message in messages))

    def test_send_missing_credentials_is_graceful(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            constitution = root / "core" / "knowledge" / "CONSTITUTION.md"
            constitution.parent.mkdir(parents=True)
            constitution.write_text("# Full Potential Constitution\n\nbody", encoding="utf-8")

            with mock.patch.dict("os.environ", {}, clear=True):
                messages = surface.surface_to_telegram(
                    repo_root=root,
                    send=True,
                    creds_path=root / "missing.env",
                )

        self.assertEqual(len(messages), 1)

    def test_state_file_prevents_duplicate_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            constitution = root / "core" / "knowledge" / "CONSTITUTION.md"
            state_file = root / "sent.marker"
            constitution.parent.mkdir(parents=True)
            constitution.write_text("# Full Potential Constitution\n\nbody", encoding="utf-8")
            state_file.write_text("already\n", encoding="utf-8")

            with mock.patch.object(surface, "send_message") as send_message:
                messages = surface.surface_to_telegram(
                    repo_root=root,
                    send=True,
                    state_file=state_file,
                    force=False,
                )

        self.assertEqual(len(messages), 1)
        send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()

