from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).with_name("scout_run.py")
SPEC = importlib.util.spec_from_file_location("scout_run", MODULE)
assert SPEC and SPEC.loader
scout_run = importlib.util.module_from_spec(SPEC)
sys.modules["scout_run"] = scout_run
SPEC.loader.exec_module(scout_run)


class ScoutRunTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-scout-run-"))

    def fixture(self, root: Path, *, news_count: int = 3, growth_count: int = 2, cost: float = 0.42) -> Path:
        payload = {
            "cost_usd": cost,
            "news": [
                {"title": f"News {idx}", "url": f"https://example.com/news-{idx}", "why": "James-relevant signal"}
                for idx in range(news_count)
            ],
            "growth": [
                {
                    "name": f"Tool {idx}",
                    "url": f"https://example.com/tool-{idx}",
                    "why": "Adoptable capability",
                    "proposed_use": "Review for scout_adopt",
                    "score": "10/15",
                }
                for idx in range(growth_count)
            ],
        }
        path = root / "fixture.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def seed_vault(self, root: Path) -> Path:
        vault = root / "vault"
        (vault / "00_MEMORY").mkdir(parents=True)
        (vault / "00_MEMORY" / "NEWS FOR YOU.md").write_text("status: stalled\nold news\n", encoding="utf-8")
        (vault / "00_MEMORY" / "AI GROWTH FEED.md").write_text("status: stalled\nold growth\n", encoding="utf-8")
        (vault / "00_MEMORY" / "COST LEDGER.md").write_text("# COST LEDGER\n", encoding="utf-8")
        (vault / "00_MEMORY" / "PROOF LOG.md").write_text("# PROOF LOG\n", encoding="utf-8")
        return vault

    def test_success_writes_both_feeds_cost_proof_and_cursor(self) -> None:
        root = self.root()
        vault = self.seed_vault(root)
        config = root / "config"
        result = scout_run.run_if_due(
            vault=vault,
            config_dir=config,
            cursor_path=config / "last_run.txt",
            disabled_path=config / ".disabled",
            fixture_path=self.fixture(root),
            today="2026-06-11",
        )

        self.assertEqual(result.status, "live")
        news = (vault / "00_MEMORY" / "NEWS FOR YOU.md").read_text(encoding="utf-8")
        growth = (vault / "00_MEMORY" / "AI GROWTH FEED.md").read_text(encoding="utf-8")
        self.assertIn("status: live (scout pipe - last run 2026-06-11)", news)
        self.assertEqual(news.count("https://example.com/news-"), 3)
        self.assertIn("Tool 0", growth)
        self.assertIn("World Scout run - $0.42", (vault / "00_MEMORY" / "COST LEDGER.md").read_text())
        self.assertIn("World Scout outward feeds refreshed", (vault / "00_MEMORY" / "PROOF LOG.md").read_text())
        self.assertFalse((vault / "COST LEDGER.md").exists())  # no root duplicate surface
        self.assertFalse((vault / "PROOF LOG.md").exists())
        self.assertEqual((config / "last_run.txt").read_text(encoding="utf-8").strip(), "2026-06-11")

    def test_dry_run_writes_nothing(self) -> None:
        root = self.root()
        vault = self.seed_vault(root)
        before = (vault / "00_MEMORY" / "NEWS FOR YOU.md").read_text(encoding="utf-8")

        result = scout_run.run_if_due(
            vault=vault,
            config_dir=root / "config",
            cursor_path=root / "config" / "last_run.txt",
            disabled_path=root / "config" / ".disabled",
            fixture_path=self.fixture(root),
            today="2026-06-11",
            dry_run=True,
        )

        self.assertEqual(result.status, "dry-run")
        self.assertEqual((vault / "00_MEMORY" / "NEWS FOR YOU.md").read_text(encoding="utf-8"), before)
        self.assertFalse((root / "config" / "last_run.txt").exists())

    def test_failure_leaves_notes_stalled_and_untouched(self) -> None:
        root = self.root()
        vault = self.seed_vault(root)
        fixture = self.fixture(root, news_count=2)
        before_news = (vault / "00_MEMORY" / "NEWS FOR YOU.md").read_text(encoding="utf-8")
        before_growth = (vault / "00_MEMORY" / "AI GROWTH FEED.md").read_text(encoding="utf-8")

        with self.assertRaises(scout_run.ScoutRunError):
            scout_run.run_if_due(
                vault=vault,
                config_dir=root / "config",
                cursor_path=root / "config" / "last_run.txt",
                disabled_path=root / "config" / ".disabled",
                fixture_path=fixture,
                today="2026-06-11",
            )

        self.assertEqual((vault / "00_MEMORY" / "NEWS FOR YOU.md").read_text(encoding="utf-8"), before_news)
        self.assertEqual((vault / "00_MEMORY" / "AI GROWTH FEED.md").read_text(encoding="utf-8"), before_growth)

    def test_once_per_day_and_kill_switch(self) -> None:
        root = self.root()
        vault = self.seed_vault(root)
        config = root / "config"
        config.mkdir()
        (config / "last_run.txt").write_text("2026-06-11\n", encoding="utf-8")

        skipped = scout_run.run_if_due(
            vault=vault,
            config_dir=config,
            cursor_path=config / "last_run.txt",
            disabled_path=config / ".disabled",
            fixture_path=self.fixture(root),
            today="2026-06-11",
        )
        self.assertEqual(skipped.status, "skipped")

        (config / ".disabled").write_text("1\n", encoding="utf-8")
        disabled = scout_run.run_if_due(
            vault=vault,
            config_dir=config,
            cursor_path=config / "last_run.txt",
            disabled_path=config / ".disabled",
            fixture_path=self.fixture(root),
            force=True,
            today="2026-06-11",
        )
        self.assertEqual(disabled.status, "disabled")

    def test_cost_cap_blocks_writes(self) -> None:
        root = self.root()
        vault = self.seed_vault(root)

        with self.assertRaises(scout_run.ScoutRunError):
            scout_run.run_if_due(
                vault=vault,
                config_dir=root / "config",
                cursor_path=root / "config" / "last_run.txt",
                disabled_path=root / "config" / ".disabled",
                fixture_path=self.fixture(root, cost=2.00),
                today="2026-06-11",
            )


if __name__ == "__main__":
    unittest.main()
