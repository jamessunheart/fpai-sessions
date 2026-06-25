from __future__ import annotations

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.learning import finetune_runner


class FinetuneRunnerTest(unittest.TestCase):
    def write_dataset(self, path: Path, rows: int) -> None:
        path.write_text(
            "\n".join('{"source":"brain_index.corrections","messages":[{"role":"system","content":"x"}]}' for _ in range(rows)) + "\n",
            encoding="utf-8",
        )

    def write_signals(self, path: Path, rows: int) -> None:
        payload = {
            "task_id": "task",
            "signal_type": "correction",
            "prompt": "prompt",
            "response": "response",
            "value": -1,
            "weight": 1,
        }
        path.write_text("\n".join(json.dumps(payload) for _ in range(rows)) + "\n", encoding="utf-8")

    def write_directive(self, path: Path) -> None:
        path.write_text(
            json.dumps({"weighting": {"correction": 1.5, "approval": 0.8, "reversal": 1.8, "merge_outcome": 1.2, "engagement": 1.3, "council_verdict": 1.0}}),
            encoding="utf-8",
        )

    def test_blocks_without_explicit_approval_or_gpu(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-finetune-"))
        dataset = root / "dataset.jsonl"
        self.write_dataset(dataset, finetune_runner.MIN_EXAMPLES)
        signals = root / "signals.jsonl"
        self.write_signals(signals, finetune_runner.MIN_SIGNALS)
        directive = root / "directive.json"
        self.write_directive(directive)
        benchmarks = root / "scores.jsonl"
        benchmarks.write_text('{"agent":"forge"}\n', encoding="utf-8")

        with patch.dict(os.environ, {"LEARNING_ENABLED": "1", "FINETUNE_APPROVED": "0", "HAS_GPU": "0"}, clear=False):
            plan = finetune_runner.build_plan(dataset=dataset, benchmark_ledger=benchmarks, signal_ledger=signals, directive_path=directive)

        self.assertFalse(plan["ready_to_train"])
        self.assertEqual(finetune_runner.run_training(plan, execute=True)["status"], "blocked_by_gates")

    def test_ready_requires_execute_even_when_all_gates_pass(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-finetune-ready-"))
        dataset = root / "dataset.jsonl"
        self.write_dataset(dataset, finetune_runner.MIN_EXAMPLES)
        signals = root / "signals.jsonl"
        self.write_signals(signals, finetune_runner.MIN_SIGNALS)
        directive = root / "directive.json"
        self.write_directive(directive)
        benchmarks = root / "scores.jsonl"
        benchmarks.write_text('{"agent":"forge"}\n', encoding="utf-8")

        with patch.dict(os.environ, {"LEARNING_ENABLED": "1", "FINETUNE_APPROVED": "1", "HAS_GPU": "1"}, clear=False):
            plan = finetune_runner.build_plan(dataset=dataset, benchmark_ledger=benchmarks, signal_ledger=signals, directive_path=directive)

        self.assertTrue(plan["ready_to_train"])
        self.assertEqual(finetune_runner.run_training(plan, execute=False)["status"], "ready_requires_execute")

    def test_small_dataset_never_ready_even_with_approval_and_gpu(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-finetune-small-"))
        dataset = root / "dataset.jsonl"
        self.write_dataset(dataset, 1)
        signals = root / "signals.jsonl"
        self.write_signals(signals, finetune_runner.MIN_SIGNALS)
        directive = root / "directive.json"
        self.write_directive(directive)
        benchmarks = root / "scores.jsonl"
        benchmarks.write_text('{"agent":"forge"}\n', encoding="utf-8")

        with patch.dict(os.environ, {"LEARNING_ENABLED": "1", "FINETUNE_APPROVED": "1", "HAS_GPU": "1"}, clear=False):
            plan = finetune_runner.build_plan(dataset=dataset, benchmark_ledger=benchmarks, signal_ledger=signals, directive_path=directive)

        self.assertFalse(plan["ready_to_train"])
        self.assertFalse(plan["gates"]["min_examples_met"])
        self.assertFalse(plan["gates"]["min_corrections_met"])

    def test_weighted_corpus_uses_directive_weight(self) -> None:
        rows = [{"signal_type": "correction", "prompt": "p", "response": "r", "value": -1, "weight": 2}]
        corpus = finetune_runner.build_weighted_corpus(rows, {"weighting": {"correction": 1.5}})

        self.assertEqual(corpus[0]["weight"], 3.0)

    def test_records_model_version_without_live_db(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-model-version-"))
        path = root / "versions.jsonl"

        result = finetune_runner.record_model_version("fpai-llama:v1", signal_count=100, metrics={"score_delta": 0.1}, path=path)

        self.assertEqual(result, path)
        self.assertIn("fpai-llama:v1", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
