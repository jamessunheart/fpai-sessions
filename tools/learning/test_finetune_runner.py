from __future__ import annotations

import os
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

    def test_blocks_without_explicit_approval_or_gpu(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-finetune-"))
        dataset = root / "dataset.jsonl"
        self.write_dataset(dataset, finetune_runner.MIN_EXAMPLES)
        benchmarks = root / "scores.jsonl"
        benchmarks.write_text('{"agent":"forge"}\n', encoding="utf-8")

        with patch.dict(os.environ, {"FINETUNE_APPROVED": "0", "HAS_GPU": "0"}, clear=False):
            plan = finetune_runner.build_plan(dataset=dataset, benchmark_ledger=benchmarks)

        self.assertFalse(plan["ready_to_train"])
        self.assertEqual(finetune_runner.run_training(plan, execute=True)["status"], "blocked_by_gates")

    def test_ready_requires_execute_even_when_all_gates_pass(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-finetune-ready-"))
        dataset = root / "dataset.jsonl"
        self.write_dataset(dataset, finetune_runner.MIN_EXAMPLES)
        benchmarks = root / "scores.jsonl"
        benchmarks.write_text('{"agent":"forge"}\n', encoding="utf-8")

        with patch.dict(os.environ, {"FINETUNE_APPROVED": "1", "HAS_GPU": "1"}, clear=False):
            plan = finetune_runner.build_plan(dataset=dataset, benchmark_ledger=benchmarks)

        self.assertTrue(plan["ready_to_train"])
        self.assertEqual(finetune_runner.run_training(plan, execute=False)["status"], "ready_requires_execute")

    def test_small_dataset_never_ready_even_with_approval_and_gpu(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-finetune-small-"))
        dataset = root / "dataset.jsonl"
        self.write_dataset(dataset, 1)
        benchmarks = root / "scores.jsonl"
        benchmarks.write_text('{"agent":"forge"}\n', encoding="utf-8")

        with patch.dict(os.environ, {"FINETUNE_APPROVED": "1", "HAS_GPU": "1"}, clear=False):
            plan = finetune_runner.build_plan(dataset=dataset, benchmark_ledger=benchmarks)

        self.assertFalse(plan["ready_to_train"])
        self.assertFalse(plan["gates"]["min_examples_met"])
        self.assertFalse(plan["gates"]["min_corrections_met"])


if __name__ == "__main__":
    unittest.main()
