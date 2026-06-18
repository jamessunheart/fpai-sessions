from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.benchmarks import beacon_scorer, council_scorer, ember_scorer, forge_scorer, hermes_scorer, loop_scorer, spark_scorer, steward_scorer
from tools.benchmarks.improvement_proposer import propose_for_score
from tools.benchmarks.run_all_benchmarks import SCORERS, run_all

NOW = dt.datetime(2026, 6, 17, 6, 0, tzinfo=dt.timezone.utc)


class PerAgentBenchmarksTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-d073-benchmarks-"))

    def fixture_data(self) -> dict:
        old = "2026-06-16T06:00:00Z"
        return {
            "probe_pool": [
                {"source": "reddit", "created_at": old, "discovery_score": 0.8, "contacted": True}
                for _ in range(12)
            ],
            "probe_sessions": [
                {"source": "reddit", "platform": "email", "engaged": False, "sent": True, "message_count": 2}
                for _ in range(22)
            ]
            + [{"source": "reddit", "platform": "email", "engaged": True, "sent": True, "message_count": 4, "completed_spark": True}],
            "corrections": [{"created_at": old} for _ in range(8)],
            "alignment_modified_at": "2026-06-10T00:00:00Z",
            "ops_ledger": [
                {"ts": old, "event": "ran"},
                {"ts": old, "event": "failed"},
                {"ts": old, "event": "benchmark_run"},
                {"ts": old, "event": "cost", "cost_usd": 1.0},
            ],
            "decisions": [
                {"proposed_by": "council", "build_status": "built", "review_status": "REQUEST_CHANGES"},
                {"proposed_by": "council", "build_status": "queued", "review_status": ""},
            ],
            "council_debates": [{"converged": True}, {"converged": False}],
            "registry_builds": [
                {"id": "SPEC_a", "status": "done", "tests_passed": True, "notes": "auto-queued:beacon"},
                {"id": "SPEC_b", "status": "done", "tests_passed": True},
            ],
            "review_statuses": {"SPEC_a": ["REQUEST_CHANGES", "APPROVE"], "SPEC_b": ["APPROVE"]},
            "per_agent_scores": [
                {"agent": "beacon", "run_date": "2026-06-03", "primary_metric": 0.5},
                {"agent": "beacon", "run_date": "2026-06-17", "primary_metric": 0.51},
            ],
            "known_event_types": ["ran", "failed", "benchmark_run", "cost"],
            "estimated_cost_per_send": {"email": 0.01},
        }

    def test_each_scorer_returns_shape_with_primary_metric(self) -> None:
        data = self.fixture_data()
        for scorer in (beacon_scorer, spark_scorer, ember_scorer, hermes_scorer, council_scorer, forge_scorer, steward_scorer, loop_scorer):
            with self.subTest(agent=scorer.AGENT):
                result = scorer.score(data, now=NOW)
                self.assertEqual(result["agent"], scorer.AGENT)
                self.assertIn("primary_metric", result)
                self.assertIsInstance(result["metrics"], dict)
                self.assertIn("trigger_fired", result)

    def test_improvement_proposer_does_not_fire_without_trigger(self) -> None:
        root = self.root()
        queued = mock.Mock()
        result = propose_for_score(
            {"agent": "forge", "primary_metric": 0.9, "metrics": {}, "trigger_fired": False},
            proposal_log=root / "proposals.jsonl",
            queue_build=queued,
            now=NOW,
        )
        self.assertIsNone(result)
        queued.assert_not_called()

    def test_improvement_proposer_queues_when_trigger_fires(self) -> None:
        root = self.root()
        ops = root / "ops.jsonl"
        ops.write_text(
            json.dumps({"ts": "2026-06-16T00:00:00Z", "event": "correction", "agent": "forge", "detail": "Forge missed rollback evidence."}) + "\n",
            encoding="utf-8",
        )
        inventory = root / "AVAILABLE_RESOURCES.md"
        inventory.write_text(
            "# Available Resources\n\n## CLIs\n\n- git: /usr/bin/git\n\n## Python-libs\n\n- fastapi==0.109.0\n",
            encoding="utf-8",
        )
        platform_bias = root / "PLATFORM_BIAS_REGISTRY.md"
        platform_bias.write_text(
            "# Platform Bias Registry\n\n"
            "## Sovereign Rating Rubric\n\n"
            "| Rating | Meaning | Default handling |\n"
            "|---|---|---|\n"
            "| Sovereign | local-first | prefer |\n",
            encoding="utf-8",
        )
        queued = mock.Mock(return_value="d999")
        drafted = mock.Mock(return_value="# Improve Forge\n")
        result = propose_for_score(
            {
                "agent": "forge",
                "primary_metric": 0.54,
                "metrics": {"first_pass_approve_rate": 0.54},
                "trigger_fired": True,
                "trigger_metric": "first_pass_approve_rate",
                "trigger_reason": "below threshold",
            },
            proposal_log=root / "proposals.jsonl",
            ops_ledger=ops,
            claude_runner=drafted,
            queue_build=queued,
            now=NOW,
            resource_inventory_path=inventory,
            platform_bias_registry_path=platform_bias,
        )
        self.assertEqual(result["spec_queued"], "d999")
        drafted.assert_called_once()
        prompt = drafted.call_args.args[0]
        self.assertIn("Forge missed rollback evidence", prompt)
        self.assertIn("Available resources on server 162", prompt)
        self.assertIn("Sovereignty check", prompt)
        self.assertIn("Sovereign/Hybrid/Dependent", prompt)
        self.assertIn("git: /usr/bin/git", prompt)
        self.assertIn("fastapi==0.109.0", prompt)
        queued.assert_called_once_with("# Improve Forge\n")

    def test_loop_triggers_on_14_day_flatline_with_sparse_data(self) -> None:
        result = loop_scorer.score(
            {
                "per_agent_scores": [
                    {"agent": "beacon", "run_date": "2026-06-03", "primary_metric": 0.5},
                    {"agent": "beacon", "run_date": "2026-06-17", "primary_metric": 0.51},
                ],
                "registry_builds": [],
                "ops_ledger": [],
            },
            now=NOW,
        )
        self.assertTrue(result["trigger_fired"])
        self.assertEqual(result["trigger_metric"], "improvement_velocity")

    def test_run_all_writes_one_row_per_agent_to_jsonl(self) -> None:
        root = self.root()
        fixture = root / "fixture.json"
        fixture.write_text(json.dumps(self.fixture_data()), encoding="utf-8")
        score_ledger = root / "scores.jsonl"
        result = run_all(
            fixture=fixture,
            score_ledger=score_ledger,
            proposal_log=root / "proposals.jsonl",
            ops_ledger=root / "ops.jsonl",
            registry_path=root / "missing-registry.json",
            queue_improvements=False,
            current=NOW,
        )
        self.assertFalse(result["errors"])
        rows = [json.loads(line) for line in score_ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), len(SCORERS))
        self.assertEqual({row["agent"] for row in rows}, {scorer.AGENT for scorer in SCORERS})
        self.assertTrue((root / "baseline_2026-06-17.json").exists())

    def test_benchmarks_disable_exits_cleanly(self) -> None:
        root = self.root()
        with mock.patch.dict(os.environ, {"BENCHMARKS_DISABLE": "1"}):
            result = run_all(score_ledger=root / "scores.jsonl", ops_ledger=root / "ops.jsonl", current=NOW)
        self.assertTrue(result["disabled"])
        self.assertFalse((root / "scores.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
