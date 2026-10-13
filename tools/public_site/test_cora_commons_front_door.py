from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "sites" / "fullpotential-com" / "index.html"
CORA = ROOT / "sites" / "fullpotential-com" / "coracommons" / "index.html"
CONNECT = ROOT / "sites" / "fullpotential-com" / "coracommons" / "connect" / "index.html"


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
        self.assertIn("There is no separate Cora account to create yet", html)
        self.assertIn("Connect your agent in 60 seconds", html)
        self.assertIn("https://github.com/jamessunheart/cora-commons", html)
        self.assertIn("issues/new?template=need.yml", html)
        self.assertIn('href="/coracommons/connect/"', html)
        self.assertIn("issues/new?template=connect.yml", html)
        self.assertIn('href="/dream-big/"', html)
        self.assertIn('href="https://zenvillagecr.com/book"', html)

    def test_homepage_introduces_builder_path(self) -> None:
        html = HOME.read_text(encoding="utf-8")
        self.assertIn("Build Cora", html)
        self.assertIn("Understand it and connect your agent", html)

    def test_agent_connection_page_has_working_copy_path(self) -> None:
        html = CONNECT.read_text(encoding="utf-8")
        self.assertIn('id="agent-prompt"', html)
        self.assertIn('id="copy-prompt"', html)
        self.assertIn("navigator.clipboard.writeText", html)
        self.assertIn("Read these canonical public sources", html)
        self.assertIn("issues/new?template=connect.yml", html)
        self.assertIn("blob/main/MCP.md", html)
        self.assertIn("search Needs, match capabilities, draft proposals", html)
        self.assertIn("https://fullpotential.com/mcp", html)
        self.assertIn('id="copy-mcp"', html)


if __name__ == "__main__":
    unittest.main()
