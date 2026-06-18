from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.learning import cell_split


class CellSplitTest(unittest.TestCase):
    def test_blocks_without_approval(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-cell-block-"))
        model_dna = root / "MODEL_DNA.md"
        model_dna.write_text("canonical routing heuristic\n", encoding="utf-8")

        with patch.dict("os.environ", {"CELL_SPLIT_APPROVED": "0"}, clear=False):
            with self.assertRaises(cell_split.CellSplitBlocked):
                cell_split.generate_template("new instance", output_root=root / "dist", model_dna_path=model_dna)

    def test_generates_template_without_personal_dna(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-cell-"))
        model_dna = root / "MODEL_DNA.md"
        model_dna.write_text("canonical routing heuristic\nquality threshold\n", encoding="utf-8")

        target = cell_split.generate_template(
            "new instance",
            output_root=root / "dist",
            model_dna_path=model_dna,
            approved_override=True,
        )

        self.assertTrue((target / "core" / "STATE" / "MODEL_DNA.md").exists())
        self.assertTrue((target / "cell_split_manifest.json").exists())
        self.assertEqual(cell_split.scan_for_personal_markers(target), [])

    def test_sanitizes_source_instance_names(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-cell-sanitize-"))
        model_dna = root / "MODEL_DNA.md"
        model_dna.write_text("James-specific correction\nDomain vocabulary (CORA, Zen Village, etc.)\n", encoding="utf-8")

        target = cell_split.generate_template("new instance", output_root=root / "dist", model_dna_path=model_dna, approved_override=True)

        exported = (target / "core" / "STATE" / "MODEL_DNA.md").read_text(encoding="utf-8")
        self.assertNotIn("James", exported)
        self.assertNotIn("CORA", exported)
        self.assertEqual(cell_split.scan_for_personal_markers(target), [])

    def test_deletes_template_if_personal_marker_leaks(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-cell-leak-"))
        model_dna = root / "MODEL_DNA.md"
        model_dna.write_text("identity/PERSONAL_DNA\n", encoding="utf-8")

        with self.assertRaises(cell_split.CellSplitBlocked):
            cell_split.generate_template("new instance", output_root=root / "dist", model_dna_path=model_dna, approved_override=True)

        self.assertFalse(any((root / "dist").glob("fpos_template_*")))


if __name__ == "__main__":
    unittest.main()
