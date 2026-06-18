from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.open_model_benchmark import qwen_moe_benchmark as qwen_bench


class QwenMoeBenchmarkTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-d108-qwen-moe-"))

    def make_fixture(self) -> Path:
        root = self.root()
        codex = root / "docs" / "codex"
        state = root / "core" / "STATE"
        codex.mkdir(parents=True)
        state.mkdir(parents=True)
        (codex / "SESSION_CONTRACT.md").write_text(
            "# Contract\n\n"
            "Branch off feat/headless-build, register in REGISTRY, run tests, and wait for merge review. "
            "The build loop protects branches and specs from collision.\n",
            encoding="utf-8",
        )
        (codex / "AI_PROTOCOLS.md").write_text(
            "# AI Protocols\n\n"
            "Reserved Class decisions stop at James gates. The Resource Discipline Gate prevents unsafe spend. "
            "Proof rows name intent solved, unlocks next, proof, and next move.\n",
            encoding="utf-8",
        )
        (state / "NORTH_STAR.md").write_text(
            "# North Star\n\n"
            "Sovereign benchmark proof should compare local open models, latency, cost, evidence, and rollback risk.\n",
            encoding="utf-8",
        )
        return root

    def test_builds_qwen_moe_task_pack(self) -> None:
        tasks = qwen_bench.build_tasks(self.make_fixture(), max_sources=3)

        self.assertGreaterEqual(len(tasks), 3)
        self.assertTrue(all(task["task_id"].startswith("qwen-moe-") for task in tasks))
        self.assertTrue(all(task["expected_terms"] for task in tasks))
        self.assertTrue({task["category"] for task in tasks} <= set(qwen_bench.TASK_CATEGORIES))

    def test_scores_candidate_claim_against_llama_baseline(self) -> None:
        tasks = qwen_bench.build_tasks(self.make_fixture(), max_sources=2)
        responses = []
        for task in tasks:
            terms = " ".join(task["expected_terms"])
            responses.append(
                {
                    "model": "qwen3:30b-a3b",
                    "task_id": task["task_id"],
                    "response": json.dumps(
                        {
                            "decision": "supported",
                            "evidence": f"{terms} because source evidence supports proof and rollback risk",
                            "risk": "low",
                            "confidence": 0.87,
                        }
                    ),
                    "latency_ms": 24000,
                }
            )
            responses.append(
                {
                    "model": "llama3.1:8b",
                    "task_id": task["task_id"],
                    "response": '{"decision":"partial","evidence":"source","risk":"unknown","confidence":0.55}',
                    "latency_ms": 18000,
                }
            )

        scores = qwen_bench.score_responses(tasks, responses)
        comparison = scores["comparison"]

        self.assertEqual(comparison["status"], "scored")
        self.assertTrue(comparison["candidate_meets_claim"])
        self.assertGreaterEqual(comparison["quality_delta_vs_llama"], 0)
        self.assertEqual(comparison["active_compute_ratio_vs_llama"], 0.375)
        qwen = next(row for row in scores["models"] if row["model"] == "qwen3-30b-a3b")
        llama = next(row for row in scores["models"] if row["model"] == "llama3.1-8b")
        self.assertGreater(qwen["quality_per_active_b"], llama["quality_per_active_b"])

    def test_report_without_responses_is_task_pack_only(self) -> None:
        report = qwen_bench.build_report(root=self.make_fixture(), max_sources=2)

        self.assertEqual(report["schema"], qwen_bench.SCHEMA)
        self.assertEqual(report["mode"], "task-pack")
        self.assertNotIn("scores", report)
        self.assertEqual(report["models"]["qwen3-30b-a3b"]["active_params_b"], 3.0)

    def test_ollama_runner_is_bounded_and_uses_expected_model_refs(self) -> None:
        tasks = qwen_bench.build_tasks(self.make_fixture(), max_sources=1)
        calls: list[list[str]] = []

        def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="evidence confidence proof", stderr="")

        rows = qwen_bench.run_ollama_tasks(tasks, max_tasks=1, runner=fake_run)

        self.assertEqual(len(rows), 2)
        self.assertIn(["ollama", "run", "qwen3:30b-a3b", tasks[0]["prompt"]], calls)
        self.assertIn(["ollama", "run", "llama3.1:8b", tasks[0]["prompt"]], calls)

    def test_write_outputs(self) -> None:
        root = self.root()
        report = qwen_bench.build_report(root=self.make_fixture(), max_sources=2)
        json_path = qwen_bench.write_json(report, root / "report.json")
        md_path = qwen_bench.write_markdown(report, root / "state.md")

        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())
        self.assertIn("task pack is ready", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
