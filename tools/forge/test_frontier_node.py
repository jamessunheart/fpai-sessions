from __future__ import annotations

import datetime as dt
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.forge.publish_frontier_log import prepare_public_frontier_log, publish_release
from tools.forge.public_benchmarks import summarize_scores, write_public_benchmarks
from tools.forge.security_gate import sanitize_markdown
from tools.forge.track_upstream import parse_opportunities, update_log_from_text


NOW = dt.datetime(2026, 6, 18, 12, 0, tzinfo=dt.timezone.utc)


class FrontierNodeTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-d100-frontier-"))

    def test_security_gate_strips_private_layer(self) -> None:
        result = sanitize_markdown(
            "# Frontier\n\n"
            "- ADOPT: GEPA prompt evolution pattern\n"
            "- Contact james@example.com about probe_pool corrections\n"
            "- token should never publish\n"
        )
        self.assertFalse(result.blocked)
        self.assertIn("GEPA prompt evolution pattern", result.sanitized)
        self.assertNotIn("james@example.com", result.sanitized)
        self.assertNotIn("probe_pool", result.sanitized)
        self.assertNotIn("token should never publish", result.sanitized)
        self.assertIn("email", result.warnings)

    def test_prepare_public_frontier_log_writes_sanitized_artifact(self) -> None:
        root = self.root()
        source = root / "FRONTIER_LOG.md"
        output = root / "FRONTIER_LOG.public.md"
        source.write_text(
            "# Rolling Log\n\n"
            "- WATCH: Pipecat realtime voice adapter [score 8]\n"
            "- private contact: seeker@example.com\n",
            encoding="utf-8",
        )
        result = prepare_public_frontier_log(source=source, output=output, current=NOW)
        self.assertEqual(result["output"], str(output))
        text = output.read_text(encoding="utf-8")
        self.assertIn("FPOS Frontier Log", text)
        self.assertIn("Pipecat realtime voice adapter", text)
        self.assertNotIn("seeker@example.com", text)

    def test_publish_release_requires_explicit_env_gate(self) -> None:
        root = self.root()
        artifact = root / "frontier.md"
        artifact.write_text("# ok\n", encoding="utf-8")
        runner = mock.Mock()
        result = publish_release(artifact=artifact, tag="frontier-log-2026-06-18", title="FPOS Frontier Log", runner=runner)
        self.assertFalse(result["published"])
        runner.assert_not_called()

    def test_publish_release_calls_gh_when_approved(self) -> None:
        root = self.root()
        artifact = root / "frontier.md"
        artifact.write_text("# ok\n", encoding="utf-8")
        completed = subprocess.CompletedProcess(["gh"], 0, stdout="ok", stderr="")
        runner = mock.Mock(return_value=completed)
        with mock.patch.dict("os.environ", {"FRONTIER_PUBLISH_APPROVED": "1"}):
            result = publish_release(artifact=artifact, tag="frontier-log-2026-06-18", title="FPOS Frontier Log", runner=runner)
        self.assertTrue(result["published"])
        self.assertEqual(runner.call_args.args[0][0:3], ["gh", "release", "create"])

    def test_track_upstream_extracts_contribute_lines_and_drafts_review_gate(self) -> None:
        root = self.root()
        output = root / "UPSTREAM_CONTRIBUTIONS.md"
        text = (
            "CONTRIBUTE: Pipecat - add a documented local transport fixture - PR complexity: low\n"
            "- CONTRIBUTE: Cognee - clarify schema migration rollback docs - PR complexity: med\n"
        )
        opportunities = parse_opportunities(text)
        self.assertEqual([item.project for item in opportunities], ["Pipecat", "Cognee"])
        result = update_log_from_text(text, output=output, current=NOW)
        self.assertEqual(result["count"], 2)
        rendered = output.read_text(encoding="utf-8")
        self.assertIn("Council review required", rendered)
        self.assertIn("| Pipecat | add a documented local transport fixture | low | draft |", rendered)

    def test_public_benchmarks_gate_requires_three_points(self) -> None:
        rows = [
            {"agent": "forge", "run_date": "2026-06-16", "primary_metric": 0.5},
            {"agent": "forge", "run_date": "2026-06-17", "primary_metric": 0.6},
            {"agent": "forge", "run_date": "2026-06-18", "primary_metric": 0.7},
            {"agent": "ember", "run_date": "2026-06-18", "primary_metric": 0.9},
        ]
        summary = summarize_scores(rows, min_points=3)
        self.assertEqual([item["agent"] for item in summary["agents"]], ["forge"])
        self.assertEqual(summary["agents"][0]["delta_from_first"], 0.2)
        self.assertEqual(summary["skipped"][0]["agent"], "ember")

    def test_write_public_benchmarks_writes_leaderboard_and_result(self) -> None:
        root = self.root()
        ledger = root / "scores.jsonl"
        ledger.write_text(
            "\n".join(
                json.dumps({"agent": "forge", "run_date": day, "primary_metric": metric})
                for day, metric in (("2026-06-16", 0.5), ("2026-06-17", 0.6), ("2026-06-18", 0.7))
            )
            + "\n",
            encoding="utf-8",
        )
        result = write_public_benchmarks(score_ledger=ledger, public_dir=root / "benchmarks", current=NOW)
        self.assertEqual(result["agents_published"], 1)
        self.assertTrue((root / "benchmarks" / "leaderboard.md").exists())
        self.assertTrue((root / "benchmarks" / "results" / "2026-06-18.md").exists())


if __name__ == "__main__":
    unittest.main()
