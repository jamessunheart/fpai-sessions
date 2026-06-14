from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.spec.draft import SpecAlreadyExistsError, draft_path_for, draft_spec, render_spec


class SpecDraftTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-spec-draft-"))

    def intent(self) -> dict[str, object]:
        return {
            "id": "rung4-hubs",
            "title": "Rung 4 hubs",
            "next": "apprentice fleet builds comms, financial, and recruiting hubs",
            "stream": "Game",
            "weight": 70,
        }

    def test_intent_without_spec_writes_well_formed_draft(self) -> None:
        root = self.root()

        path = draft_spec(self.intent(), specs_dir=root)

        self.assertEqual(path.name, "SPEC_rung4-hubs.draft.md")
        text = path.read_text(encoding="utf-8")
        self.assertIn("DRAFT - review before dispatch", text)
        self.assertIn("auto-dispatch", text)
        self.assertIn("auto-build", text)
        self.assertIn("## The three declarations", text)
        self.assertIn("**Milestone (DoD):**", text)
        self.assertIn("**Dependency:** TODO(review):", text)
        self.assertIn("**Landing target:** TODO(review):", text)
        self.assertIn("TODO(review):", text)
        self.assertIn("## Rollback", text)

    def test_existing_promoted_spec_is_not_overwritten(self) -> None:
        root = self.root()
        promoted = root / "SPEC_rung4-hubs.md"
        promoted.write_text("# keep me\n", encoding="utf-8")

        with self.assertRaises(SpecAlreadyExistsError):
            draft_spec(self.intent(), specs_dir=root)

        self.assertEqual(promoted.read_text(encoding="utf-8"), "# keep me\n")
        self.assertFalse((root / "SPEC_rung4-hubs.draft.md").exists())

    def test_existing_draft_is_not_overwritten(self) -> None:
        root = self.root()
        draft = root / "SPEC_rung4-hubs.draft.md"
        draft.write_text("# existing draft\n", encoding="utf-8")

        with self.assertRaises(FileExistsError):
            draft_spec(self.intent(), specs_dir=root)

        self.assertEqual(draft.read_text(encoding="utf-8"), "# existing draft\n")

    def test_missing_info_gets_todo_review_markers(self) -> None:
        text = render_spec({"id": "thin-intent", "next": "draft a thing"})

        self.assertIn("TODO(review): add source notes", text)
        self.assertIn("TODO(review): confirm dependency before build", text)
        self.assertIn("TODO(review): choose landing target branch", text)

    def test_dry_run_writes_nothing(self) -> None:
        root = self.root()

        path = draft_spec(self.intent(), specs_dir=root, dry_run=True)

        self.assertEqual(path, draft_path_for(self.intent(), root))
        self.assertFalse(path.exists())
        self.assertEqual(list(root.glob("*")), [])

    def test_dry_run_reports_existing_draft_without_overwriting(self) -> None:
        root = self.root()
        draft = root / "SPEC_rung4-hubs.draft.md"
        draft.write_text("# existing draft\n", encoding="utf-8")

        path = draft_spec(self.intent(), specs_dir=root, dry_run=True)

        self.assertEqual(path, draft)
        self.assertEqual(draft.read_text(encoding="utf-8"), "# existing draft\n")


if __name__ == "__main__":
    unittest.main()
