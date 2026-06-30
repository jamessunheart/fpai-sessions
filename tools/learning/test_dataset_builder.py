from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.learning import dataset_builder as builder


def correction_rows(count: int) -> list[dict[str, str]]:
    return [
        {
            "id": f"corr-{idx}",
            "context": f"Question {idx}: what should the bot do?",
            "original_response": "Ask James to decide every reversible detail.",
            "corrected_response": "Pick the reversible default, name the rollback, and keep James upstream.",
            "timestamp": "2026-06-17T00:00:00Z",
        }
        for idx in range(count)
    ]


class DatasetBuilderTest(unittest.TestCase):
    def test_exports_valid_jsonl_from_mock_corrections_table(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-learning-"))
        output = root / "dataset.jsonl"
        examples, stats = builder.build_examples(corrections=correction_rows(builder.MIN_CORRECTIONS))

        path = builder.export_jsonl(examples, output, stats=stats)

        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), builder.MIN_CORRECTIONS)
        self.assertTrue(all(row["format"] == "dpo" for row in rows))
        self.assertTrue(all(row["messages"][0]["role"] == "system" for row in rows))
        self.assertTrue(all(row["messages"][1]["role"] == "user" for row in rows))

    def test_refuses_export_if_under_min_examples(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-learning-under-"))
        output = root / "dataset.jsonl"
        examples, stats = builder.build_examples(corrections=correction_rows(builder.MIN_CORRECTIONS - 1))

        with self.assertRaises(builder.InsufficientExamples):
            builder.export_jsonl(examples, output, stats=stats)

        self.assertFalse(output.exists())

    def test_dpo_format_valid_chosen_rejected_pairs(self) -> None:
        examples, _stats = builder.build_examples(corrections=correction_rows(1))

        row = examples[0]
        builder.validate_example(row)

        self.assertEqual(row["format"], "dpo")
        self.assertEqual(row["source"], "brain_index.corrections")
        self.assertEqual(row["chosen"], [{"role": "assistant", "content": "Pick the reversible default, name the rollback, and keep James upstream."}])
        self.assertEqual(row["rejected"], [{"role": "assistant", "content": "Ask James to decide every reversible detail."}])

    def test_missing_live_context_does_not_use_internal_conversation_id_as_prompt(self) -> None:
        examples, _stats = builder.build_examples(
            corrections=[
                {
                    "conversation_id": "private-chat-123",
                    "original_response": "old answer",
                    "james_correction": "new answer",
                }
            ]
        )

        self.assertEqual(examples[0]["messages"][1]["content"], "James corrected a prior assistant answer.")
        self.assertEqual(examples[0]["metadata"]["conversation_id"], "private-chat-123")

    def test_merge_outcomes_export_sft_good_build_pattern(self) -> None:
        examples, _stats = builder.build_examples(
            corrections=[],
            merge_outcomes=[
                {
                    "spec": "SPEC_router-route-filtering",
                    "code_diff": "tools/router/route.py",
                    "verdict": "APPROVE",
                    "good_build_pattern": "Gate route:auto, escalate the rest, and test every branch.",
                }
            ],
        )

        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["format"], "sft")
        builder.validate_example(examples[0])

    def test_probe_sessions_quality_score_exports_high_quality_sft(self) -> None:
        examples, _stats = builder.build_examples(
            probe_sessions=[
                {
                    "probe_id": "p1",
                    "quality_score": 0.92,
                    "context": "Spark intake conversation",
                    "last_message": "Name the next smallest aligned step and preserve the person's autonomy.",
                }
            ]
        )

        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["source"], "brain_index.probe_sessions")
        self.assertEqual(examples[0]["format"], "sft")
        builder.validate_example(examples[0])

    def test_feature_outcomes_export_runtime_quality_examples(self) -> None:
        examples, stats = builder.build_examples(
            feature_outcomes=[
                {
                    "event": "feature_outcome",
                    "spec_id": "SPEC_runtime",
                    "metric_name": "activation_quality",
                    "baseline": "merged_before_activation",
                    "observed": "activated",
                    "delta": "activation completed",
                    "verdict": "improved",
                    "evidence": ["liveness:pass"],
                }
            ]
        )

        self.assertEqual(stats.feature_outcomes, 1)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["source"], "ops_ledger.feature_outcomes")
        self.assertEqual(examples[0]["metadata"]["training_signal"], "improved_feature_outcome")
        builder.validate_example(examples[0])

    def test_loads_feature_outcomes_from_ops_ledger_only(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-feature-outcome-loader-"))
        ledger = root / "ops.jsonl"
        ledger.write_text(
            json.dumps({"event": "feature_outcome", "spec_id": "SPEC_one", "verdict": "flat"})
            + "\n"
            + json.dumps({"event": "merge_outcome", "spec": "SPEC_two", "verdict": "approve"})
            + "\n",
            encoding="utf-8",
        )

        rows = builder.load_ops_ledger_feature_outcomes(ledger)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["spec_id"], "SPEC_one")


if __name__ == "__main__":
    unittest.main()
