from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.learn import build_preference_dataset as builder
from tools.learn import eval_judge


class LearnToolsTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-learn-"))

    def make_fixture(self) -> Path:
        root = self.root()
        brain = root / "brain_index.json"
        brain.write_text(
            json.dumps(
                {
                    "decisions": [
                        {
                            "id": "merge-1",
                            "merge_outcome": "good",
                            "prompt": "ship guarded router",
                            "decision": "route:auto wrote a guarded draft with tests",
                            "alternative": "auto-act every route without escalation",
                        },
                        {
                            "id": "merge-2",
                            "merge_outcome": "regressed",
                            "prompt": "refresh surfaces",
                            "action": "claimed proof without checking consequence",
                            "correction": "consequence ledger outweighs the vibe tag",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        memory = root / "memory"
        memory.mkdir()
        (memory / "feedback_alpha.md").write_text(
            "Prompt: answer d010\n"
            "Rejected: train on the held-out split later\n"
            "Preferred: mark held-out examples never-train forever\n",
            encoding="utf-8",
        )
        receipts = root / "DECISIONS.md"
        receipts.write_text(
            "## receipt row\n"
            "Decision: ship a proof claim from vibes only\n"
            "Receipt: tested consequence evidence before scoring\n"
            "Verdict: good\n",
            encoding="utf-8",
        )
        return root

    def test_assembler_produces_pairs_from_fixture(self) -> None:
        pairs = builder.assemble_pairs(self.make_fixture(), eval_percent=100)

        self.assertGreaterEqual(len(pairs), 4)
        self.assertTrue(all(row["preferred"]["text"] for row in pairs))
        self.assertTrue(all(row["rejected"]["text"] for row in pairs))
        self.assertTrue(all(row["never_train"] for row in pairs))
        self.assertTrue(all(row["eval"]["label"] in {"A", "B"} for row in pairs))

    def test_frozen_split_is_stable_across_runs(self) -> None:
        root = self.make_fixture()

        first = builder.assemble_pairs(root, eval_percent=50)
        second = builder.assemble_pairs(root, eval_percent=50)

        self.assertEqual(
            [(row["id"], row["split"], row["never_train"], row["eval"]) for row in first],
            [(row["id"], row["split"], row["never_train"], row["eval"]) for row in second],
        )

    def test_eval_judge_returns_number(self) -> None:
        rows = builder.assemble_pairs(self.make_fixture(), eval_percent=100)

        number = eval_judge.eval_judge(rows, lambda row: row["eval"]["A"] and "A")

        self.assertIsInstance(number, float)

    def test_eval_judge_cli_prints_one_number(self) -> None:
        root = self.make_fixture()
        dataset = root / "pairs.jsonl"
        builder.write_jsonl(builder.assemble_pairs(root, eval_percent=100), dataset)

        proc = subprocess.run(
            [sys.executable, "-B", str(Path(eval_judge.__file__)), str(dataset), "--judge", "baseline"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        self.assertRegex(proc.stdout.strip(), r"^-?\d+\.\d{6}$")
        self.assertEqual(proc.stdout.strip().count("\n"), 0)


if __name__ == "__main__":
    unittest.main()

