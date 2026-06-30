from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.curiosity import ask


class CuriosityAskTest(unittest.TestCase):
    def root(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-curiosity-"))
        (root / "core" / "BUILD" / "reviews").mkdir(parents=True)
        (root / "core" / "BUILD").mkdir(parents=True, exist_ok=True)
        (root / "core" / "STATE").mkdir(parents=True, exist_ok=True)
        (root / "core" / "BUILD" / "PROTECTED_PATHS.txt").write_text("tools/merge/\n", encoding="utf-8")
        return root

    def test_generates_one_question_from_regressed_feature_outcome(self) -> None:
        root = self.root()
        ledger = root / "ops.jsonl"
        ledger.write_text(
            json.dumps(
                {
                    "event": "feature_outcome",
                    "spec_id": "SPEC_bad",
                    "metric_name": "post_merge_activation_quality",
                    "baseline": "merged_before_activation",
                    "observed": "post_activation_checks_failed",
                    "delta": "runtime regression detected",
                    "verdict": "regressed",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        evidence = ask.collect_evidence(repo_root=root, ops_ledger=ledger)
        question = ask.generate_question(evidence, seed_prompt=ask.DEFAULT_SEED, outcome_ledger=root / "missing.jsonl")

        self.assertIsNotNone(question)
        assert question is not None
        self.assertEqual(question.route, "build")
        self.assertEqual(len(question.evidence), 1)
        self.assertIn("SPEC_bad", question.question)
        self.assertIn("runtime regression detected", question.question)

    def test_dry_run_routes_actionable_question_to_existing_decision_seed_payload(self) -> None:
        evidence = (
            ask.Evidence(
                "feature_outcome",
                "/tmp/ops.jsonl:1",
                "runtime_quality: expected -> failed; delta=runtime regression detected",
                "regressed",
                "SPEC_bad",
                120,
            ),
        )
        question = ask.Question("cq-test", "What single repair?", "build", evidence, ask.DEFAULT_SEED, "merged builds improve runtime")

        result = ask.route_question(question, execute=False, repo_root=self.root())

        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["route"], "build")
        payload = result["payload"]
        self.assertIn("curiosity_question_id", payload["build_spec"])
        self.assertIn("protected_paths", payload["build_spec"])

    def test_reserved_question_surfaces_one_human_edge_gate(self) -> None:
        root = self.root()
        queue = root / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"
        evidence = (ask.Evidence("diff_risk", "git:core/STATE/policies/x", "policy changed", "protected_path", score=110),)
        question = ask.Question(
            "cq-reserved",
            "Should we move money based on this evidence?",
            "james",
            evidence,
            ask.DEFAULT_SEED,
            "reserved work needs James",
        )

        result = ask.route_question(question, execute=True, repo_root=root, queue_path=queue)

        self.assertEqual(result["status"], "surfaced")
        self.assertTrue(queue.exists())
        self.assertIn("cq-reserved", queue.read_text(encoding="utf-8"))

    def test_append_question_row_is_evidence_traced(self) -> None:
        root = self.root()
        ledger = root / "questions.jsonl"
        evidence = (ask.Evidence("review_disagreement", "review.md", "REQUEST_CHANGES: missing test", "request_changes", "SPEC_x", 95),)
        question = ask.Question("cq-row", "What assumption failed?", "build", evidence, ask.DEFAULT_SEED, "self-review catches risks")

        row = ask.append_question_row(ledger, question, {"status": "dry_run", "route": "build"})

        saved = json.loads(ledger.read_text(encoding="utf-8"))
        self.assertEqual(saved["question_id"], "cq-row")
        self.assertEqual(saved["evidence"][0]["source"], "review.md")
        self.assertEqual(row["status"], "dry_run")

    def test_close_loop_tags_triggered_feature_outcome(self) -> None:
        root = self.root()
        questions = root / "questions.jsonl"
        outcomes = root / "outcomes.jsonl"
        ops = root / "ops.jsonl"
        questions.write_text(
            json.dumps(
                {
                    "event": "curiosity_question",
                    "question_id": "cq-one",
                    "triggered_spec_id": "SPEC_fix",
                    "route_result": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        ops.write_text(
            json.dumps({"event": "feature_outcome", "spec_id": "SPEC_fix", "verdict": "improved"})
            + "\n",
            encoding="utf-8",
        )

        tagged = ask.close_loop_from_feature_outcomes(question_ledger=questions, outcome_ledger=outcomes, ops_ledger=ops)

        self.assertEqual(len(tagged), 1)
        self.assertEqual(tagged[0]["verdict"], "improved")
        self.assertIn("curiosity_question_outcome", outcomes.read_text(encoding="utf-8"))

    def test_run_cycle_writes_at_most_one_question(self) -> None:
        root = self.root()
        ops = root / "ops.jsonl"
        qledger = root / "questions.jsonl"
        ops.write_text(
            json.dumps({"event": "feature_outcome", "spec_id": "SPEC_one", "verdict": "flat"})
            + "\n"
            + json.dumps({"event": "feature_outcome", "spec_id": "SPEC_two", "verdict": "regressed"})
            + "\n",
            encoding="utf-8",
        )
        parser = ask.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(root),
                "--ops-ledger",
                str(ops),
                "--question-ledger",
                str(qledger),
                "--outcome-ledger",
                str(root / "outcomes.jsonl"),
            ]
        )

        with patch("builtins.print"):
            rc = ask.run_cycle(args)

        self.assertEqual(rc, 0)
        self.assertEqual(len(qledger.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()

