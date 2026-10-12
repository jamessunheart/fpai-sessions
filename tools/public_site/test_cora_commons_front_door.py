from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "sites" / "fullpotential-com" / "index.html"
CORA = ROOT / "sites" / "fullpotential-com" / "coracommons" / "index.html"


class CoraCommonsFrontDoorTests(unittest.TestCase):
    def test_homepage_surfaces_three_tangible_paths(self) -> None:
        html = HOME.read_text(encoding="utf-8")
        self.assertIn('href="/coracommons/">Cora Commons', html)
        self.assertIn('href="/dream-big/">Dream Big', html)
        self.assertIn('href="https://zenvillagecr.com/book">Zen Village', html)
        self.assertIn("Start with something real", html)
        self.assertIn("Explore Cora Commons", html)

    def test_cora_page_explains_bricks_and_reward_boundary(self) -> None:
        html = CORA.read_text(encoding="utf-8")
        self.assertIn("Build intelligence", html)
        self.assertIn("verified, reusable capabilities called <strong>BRICKS</strong>", html)
        self.assertIn("Collectively Organized Resource Agreements", html)
        self.assertIn("not automatically issued for uploads", html)
        self.assertIn("Independent acceptance", html)

    def test_cora_page_has_real_next_steps(self) -> None:
        html = CORA.read_text(encoding="utf-8")
        self.assertIn("mailto:james@fullpotential.com", html)
        self.assertIn('href="/dream-big/"', html)
        self.assertIn('href="https://zenvillagecr.com/book"', html)


if __name__ == "__main__":
    unittest.main()
