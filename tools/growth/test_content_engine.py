from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.growth import content_engine as ce


class ContentEngineTests(unittest.TestCase):
    def test_generates_static_article_with_assessment_cta(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "core/STATE").mkdir(parents=True)
            (root / "core/STATE/FOUNDATION.md").write_text("Routing Reasoning Recursion", encoding="utf-8")
            out = root / "sites/fullpotential-com/learn"
            path = ce.generate_article(
                repo_root=root,
                output_dir=out,
                title="Why Most Companies Misallocate Capital",
                use_claude=False,
            )
            html = path.read_text(encoding="utf-8")
            self.assertEqual(path.name, "why-most-companies-misallocate-capital.html")
            self.assertIn("Why Most Companies Misallocate Capital", html)
            self.assertIn('href="/assessment"', html)
            self.assertIn("Start the Free Assessment", html)

    def test_picks_next_missing_editorial_title(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / "why-most-companies-misallocate-capital.html").write_text("", encoding="utf-8")
            self.assertEqual(ce.pick_next_title(out), "Hidden Cost of Fragmented Attention")

    def test_coerces_claude_json_payload(self) -> None:
        article = ce.coerce_article(
            "Knowledge Bottleneck",
            {
                "description": "desc",
                "kicker": "kick",
                "pullquote": "pull",
                "sections": [{"heading": "One", "paragraphs": ["A", "B", "C"]}],
            },
        )
        self.assertEqual(article.slug, "knowledge-bottleneck")
        self.assertEqual(article.sections, [("One", ["A", "B"])])


if __name__ == "__main__":
    unittest.main()
