from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.open_model_benchmark import benchmark


class OpenModelBenchmarkTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-d056-open-model-"))

    def make_fixture(self) -> Path:
        root = self.root()
        codex = root / "docs" / "codex"
        blueprints = root / "docs" / "blueprints"
        identity = root / "core" / "STATE" / "identity"
        codex.mkdir(parents=True)
        blueprints.mkdir(parents=True)
        identity.mkdir(parents=True)
        (codex / "SESSION_CONTRACT.md").write_text(
            "# Contract\n\n"
            "Branch off feat/headless-build, register in REGISTRY, run tests, and wait for merge review. "
            "The build loop protects specs and branches from collision.\n",
            encoding="utf-8",
        )
        (codex / "AI_PROTOCOLS.md").write_text(
            "# Doctrine\n\n"
            "The self-standing doctrine has a Resource Discipline Gate, Reserved Class boundary, and rungs. "
            "It stops at James gates and prevents unsafe autonomous spend.\n",
            encoding="utf-8",
        )
        (blueprints / "learning_loop.md").write_text(
            "# Learning Loop\n\n"
            "Feedback, preference data, eval benchmark rows, and reviewer evidence improve learning without training live models.\n",
            encoding="utf-8",
        )
        (identity / "ATTENTION.md").write_text(
            "# Attention\n\n"
            "James stays upstream in coherent attention while AI carries downstream routing and source protection.\n",
            encoding="utf-8",
        )
        return root

    def test_builds_three_rounds_per_corpus_source(self) -> None:
        tasks = benchmark.build_benchmark_tasks(self.make_fixture(), max_sources=4)

        self.assertEqual(len(tasks), 12)
        self.assertEqual({task["round_name"] for task in tasks}, {"baseline", "one_shot", "two_shot"})
        self.assertTrue(all(task["schema"] if "schema" in task else True for task in tasks))
        self.assertTrue(all(task["expected"] in benchmark.CATEGORIES for task in tasks))
        self.assertEqual([task["task_id"] for task in tasks], sorted(task["task_id"] for task in tasks))

    def test_scores_responses_and_assigns_distinct_roles(self) -> None:
        tasks = benchmark.build_benchmark_tasks(self.make_fixture(), max_sources=2)
        responses = []
        for task in tasks:
            responses.append(
                {
                    "model": "qwen",
                    "task_id": task["task_id"],
                    "response": f'{{"label":"{task["expected"]}","evidence":"{task["evidence_terms"][0]} because source says so","confidence":0.9}}',
                    "latency_ms": 1000,
                }
            )
            responses.append(
                {
                    "model": "mistral",
                    "task_id": task["task_id"],
                    "response": f'I am uncertain, but the source evidence points to {task["expected"]}.',
                    "latency_ms": 3000,
                }
            )
            responses.append(
                {
                    "model": "llama",
                    "task_id": task["task_id"],
                    "response": "unrelated answer",
                    "latency_ms": 500,
                }
            )

        report = benchmark.score_responses(tasks, responses)

        self.assertEqual(report["responses_scored"], len(responses))
        self.assertEqual([row["model"] for row in report["models"]], ["llama", "mistral", "qwen"])
        coop = report["cooperative_setup"]
        self.assertEqual(coop["authority"], "advisory-only")
        self.assertIn(coop["builder"], {"qwen", "mistral"})
        self.assertIn(coop["reviewer"], {"qwen", "mistral"})
        self.assertNotEqual(coop["builder"], "llama")
        self.assertTrue(coop["cross_checks"])

    def test_learning_gain_uses_assisted_rounds(self) -> None:
        tasks = benchmark.build_benchmark_tasks(self.make_fixture(), max_sources=1)
        responses = []
        for task in tasks:
            good = task["round_name"] != "baseline"
            responses.append(
                {
                    "model": "gemma",
                    "task_id": task["task_id"],
                    "response": task["expected"] if good else "wrong",
                }
            )

        report = benchmark.score_responses(tasks, responses)
        gemma = report["models"][0]

        self.assertGreater(gemma["learning_gain"], 0)
        self.assertEqual(gemma["baseline_accuracy"], 0.0)
        self.assertGreater(gemma["learning_accuracy"], 0)

    def test_load_jsonl_and_write_json(self) -> None:
        root = self.root()
        rows = root / "responses.jsonl"
        rows.write_text(json.dumps({"model": "qwen", "task_id": "t1", "response": "x"}) + "\n", encoding="utf-8")

        loaded = benchmark.load_jsonl(rows)
        output = benchmark.write_json({"ok": True}, root / "report.json")

        self.assertEqual(loaded[0]["model"], "qwen")
        self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()

