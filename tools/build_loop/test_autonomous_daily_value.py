import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.build_loop import autonomous_daily_value as adv


NOW_TEXT = """# CURRENT_STATE

## 🎯 CURRENT PRIORITY (The ONE Thing)

### Priority: Self-sustaining network with dual sovereignty
**Status:** active.

**Active build queue:**
- d069 — Outreach engine: FP Game Champions + email via Brevo
- d073 — Per-agent recursive benchmarks (each agent measures + improves itself)

## 🎯 GOALS — top 3 (most-important first)

| # | Goal | Target | Timeframe | Current state |
|---|---|---|---|---|
| 1 | **FPOS self-standing — Phase 0 complete** | Rung 4 hubs specced | 30 days | daily state stays current without James |
| 2 | **Watchfire / Treasury — live trading validated** | first profitable closed trade logged | 30 days | live execution needs validation |
"""


class AutonomousDailyValueTest(unittest.TestCase):
    def test_picks_first_safe_ai_advanceable_candidate(self):
        candidates = adv.extract_candidates(NOW_TEXT)
        picked = adv.pick_candidate(candidates)

        self.assertIsNotNone(picked)
        self.assertEqual(picked.text, "Self-sustaining network with dual sovereignty")

    def test_reserved_candidates_are_rejected(self):
        self.assertFalse(adv.is_safe_ai_advanceable(adv.Candidate("x", "Send outreach email to leads", 1)))
        self.assertFalse(adv.is_safe_ai_advanceable(adv.Candidate("x", "Watchfire live trading validated", 1)))
        self.assertTrue(adv.is_safe_ai_advanceable(adv.Candidate("x", "Draft state reconciler analysis", 1)))

    def test_deliver_writes_artifact_and_ledger_without_commit_or_notify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            now = root / "core" / "STATE" / "NOW.md"
            now.parent.mkdir(parents=True)
            now.write_text(NOW_TEXT, encoding="utf-8")
            out_dir = root / "core" / "BUILD" / "daily_value"
            ledger = root / "ops.jsonl"

            os.environ["AUTONOMOUS_DAILY_NOW"] = "2026-06-30T09:00:00+03:00"
            try:
                result = adv.deliver(
                    repo_root=root,
                    now_path=now,
                    out_dir=out_dir,
                    disable_file=root / ".disabled",
                    ops_ledger=ledger,
                    commit=False,
                    send_notify=False,
                )
            finally:
                os.environ.pop("AUTONOMOUS_DAILY_NOW", None)

            self.assertEqual(result.status, "written")
            artifact = out_dir / "2026-06-30.md"
            self.assertTrue(artifact.exists())
            text = artifact.read_text(encoding="utf-8")
            self.assertIn("Self-sustaining network with dual sovereignty", text)
            self.assertIn("send outreach", text.lower())
            self.assertIn('"event": "written"', ledger.read_text(encoding="utf-8"))

    def test_disable_file_short_circuits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            disable = root / ".autonomous_daily_disabled"
            disable.write_text("", encoding="utf-8")

            result = adv.deliver(
                repo_root=root,
                now_path=root / "missing.md",
                out_dir=root / "out",
                disable_file=disable,
                ops_ledger=root / "ops.jsonl",
                commit=False,
                send_notify=False,
            )

            self.assertEqual(result.status, "disabled")
            self.assertFalse((root / "out").exists())

    def test_existing_daily_artifact_skips_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            now = root / "NOW.md"
            now.write_text(NOW_TEXT, encoding="utf-8")
            out_dir = root / "daily"
            out_dir.mkdir()
            artifact = out_dir / "2026-06-30.md"
            artifact.write_text("keep me", encoding="utf-8")

            os.environ["AUTONOMOUS_DAILY_NOW"] = "2026-06-30T09:00:00+03:00"
            try:
                result = adv.deliver(
                    repo_root=root,
                    now_path=now,
                    out_dir=out_dir,
                    disable_file=root / ".disabled",
                    ops_ledger=root / "ops.jsonl",
                    commit=False,
                    send_notify=False,
                )
            finally:
                os.environ.pop("AUTONOMOUS_DAILY_NOW", None)

            self.assertEqual(result.status, "skipped")
            self.assertEqual(artifact.read_text(encoding="utf-8"), "keep me")

    def test_require_athens_hour_skips_wrong_hour(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            now = root / "NOW.md"
            now.write_text(NOW_TEXT, encoding="utf-8")

            os.environ["AUTONOMOUS_DAILY_NOW"] = "2026-06-30T08:00:00+03:00"
            try:
                result = adv.deliver(
                    repo_root=root,
                    now_path=now,
                    out_dir=root / "daily",
                    disable_file=root / ".disabled",
                    ops_ledger=root / "ops.jsonl",
                    commit=False,
                    send_notify=False,
                    require_athens_hour=9,
                )
            finally:
                os.environ.pop("AUTONOMOUS_DAILY_NOW", None)

            self.assertEqual(result.status, "skipped_time")
            self.assertFalse((root / "daily").exists())

    def test_commit_artifact_commits_only_daily_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            artifact = root / "core" / "BUILD" / "daily_value" / "2026-06-30.md"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("daily value", encoding="utf-8")
            unrelated = root / "unrelated.txt"
            unrelated.write_text("do not commit", encoding="utf-8")

            sha = adv.commit_artifact(root, artifact)

            self.assertTrue(sha)
            committed = subprocess.run(
                ["git", "show", "--name-only", "--format=", "HEAD"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.splitlines()
            self.assertEqual(committed, ["core/BUILD/daily_value/2026-06-30.md"])
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout
            self.assertIn("?? unrelated.txt", status)


if __name__ == "__main__":
    unittest.main()
