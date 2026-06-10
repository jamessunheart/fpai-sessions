from __future__ import annotations

import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path

from tools.vault import freshness


def _touch(path: Path, text: str, age_days: int, now: dt.datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    ts = (now - dt.timedelta(days=age_days)).timestamp()
    os.utime(path, (ts, ts))


class FreshnessAuditTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.now = dt.datetime(2026, 6, 10, 12, 0)
        self.vault = Path(tempfile.mkdtemp(prefix="fpai-vault-"))

    def test_stale_auto_claim_is_red(self) -> None:
        _touch(self.vault / "INDEX.md", "*(auto-generated · do not edit by hand)*", 3, self.now)
        result = freshness.audit(self.vault, self.now)
        self.assertEqual([f["file"] for f in result["findings"]["auto"]], ["INDEX.md"])

    def test_fresh_auto_claim_is_clean(self) -> None:
        _touch(self.vault / "INDEX.md", "*(auto-generated)*", 0, self.now)
        result = freshness.audit(self.vault, self.now)
        self.assertEqual(result["findings"]["auto"], [])

    def test_claimed_date_beats_mtime_for_hand_files(self) -> None:
        # fresh file, old claimed content — the original 05-30 catch
        _touch(self.vault / "00_MEMORY" / "STATE.md", "Snapshot: 2026-05-01 · streams", 0, self.now)
        result = freshness.audit(self.vault, self.now)
        (finding,) = result["findings"]["memory"]
        self.assertEqual(finding["claim_age"], 40)
        self.assertEqual(finding["age"], 40)

    def test_dated_by_design_skipped(self) -> None:
        _touch(self.vault / "07_DAILY" / "old.md", "x", 90, self.now)
        _touch(self.vault / "2026-05-31.md", "x", 90, self.now)
        result = freshness.audit(self.vault, self.now)
        self.assertEqual(result["scanned"], 0)
        self.assertEqual(result["skipped"], 2)

    def test_doctrine_mentioning_auto_is_not_auto(self) -> None:
        # "self-refreshing" discussed deep in a doc ≠ a claim about THIS file
        body = "\n" * 20 + "Rung 2: Self-refreshing surfaces regenerate after each ship."
        _touch(self.vault / "00_MEMORY" / "PROTOCOLS.md", "# Doctrine" + body, 3, self.now)
        result = freshness.audit(self.vault, self.now)
        self.assertEqual(result["findings"]["auto"], [])

    def test_composite_freshness_is_oldest_embedded_source(self) -> None:
        _touch(self.vault / "HUB.md", "*(auto-refreshed by pipes)*\n![[PANEL A]]\n![[PANEL B#x]]", 0, self.now)
        _touch(self.vault / "PANEL A.md", "fresh", 0, self.now)
        _touch(self.vault / "PANEL B.md", "old", 9, self.now)
        result = freshness.audit(self.vault, self.now)
        (finding,) = result["findings"]["auto"]
        self.assertEqual(finding["file"], "HUB.md")
        self.assertEqual(finding["age"], 9)
        self.assertEqual(finding["stale_embed"], "PANEL B")

    def test_declared_stalled_sources_dont_break_composite(self) -> None:
        _touch(self.vault / "HUB.md", "*(auto-refreshed)*\n![[FEED]]\n![[LIVE]]", 0, self.now)
        _touch(self.vault / "FEED.md", "---\nstatus: stalled (pipe unscheduled)\n---\n# Feed", 9, self.now)
        _touch(self.vault / "LIVE.md", "fresh", 0, self.now)
        result = freshness.audit(self.vault, self.now)
        self.assertEqual(result["findings"]["auto"], [])

    def test_heal_runs_only_allowlisted_scripts(self) -> None:
        _touch(self.vault / "00_MEMORY" / "INDEX OF INDEXES.md", "*(auto-generated)*", 5, self.now)
        _touch(self.vault / "ROGUE.md", "*(auto-generated)*", 5, self.now)
        ran = []
        result = freshness.write_report(self.vault, self.now, self_heal=True,
                                        runner=lambda s: ran.append(s) or True)
        self.assertEqual(ran, ["tools/index/refresh.py"])  # ROGUE has no mapping → untouched
        self.assertEqual(result["healed"], ["tools/index/refresh.py"])
        report = (self.vault / freshness.REPORT_REL).read_text(encoding="utf-8")
        self.assertIn("Self-heal ran this pass", report)

    def test_report_written_and_excludes_itself(self) -> None:
        _touch(self.vault / "00_MEMORY" / "OLD.md", "old note", 30, self.now)
        result = freshness.write_report(self.vault, self.now)
        report = (self.vault / freshness.REPORT_REL).read_text(encoding="utf-8")
        self.assertIn("`00_MEMORY/OLD.md` — **30d**", report)
        self.assertEqual(result["scanned"], 1)
        # second run: the report file itself is not audited
        result2 = freshness.audit(self.vault, self.now)
        self.assertEqual(result2["scanned"], 1)


if __name__ == "__main__":
    unittest.main()
