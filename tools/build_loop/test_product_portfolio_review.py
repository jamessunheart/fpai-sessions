#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_loop import product_portfolio_review as review


class ProductPortfolioReviewTests(unittest.TestCase):
    def test_quality_value_keep_for_functional_build_with_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "core/BUILD/results/SPEC_demo.result.md"
            result.parent.mkdir(parents=True)
            result.write_text(
                """
Summary: Built assessment endpoint that captures leads, scores payloads, and writes expected fixture output.
Tests: python3 -B -m unittest tools.demo (4 OK); py_compile; bash -n; git diff --check; smoke passed.
Proof: regression fixture produces expected allocation payload.
""",
                encoding="utf-8",
            )

            row = review.assess_candidate(
                repo_root=root,
                spec_id="SPEC_demo",
                opportunity={
                    "id": "assessment-demo",
                    "title": "Assessment Demo",
                    "allocation_score": 32,
                    "cash_proximity_score": 14,
                    "questions": {"who_pays": "Founders buying an Allocation Intelligence diagnostic."},
                },
                result_path=result,
            )

            self.assertGreaterEqual(row["quality_score"], 80)
            self.assertGreaterEqual(row["value_score"], 75)
            self.assertEqual(row["recommendation"], "keep")
            self.assertFalse(row["low_quality"])

    def test_low_quality_scaffold_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "core/BUILD/results/SPEC_stub.result.md"
            result.parent.mkdir(parents=True)
            result.write_text("Summary: placeholder scaffold only.\nTests: not run.\n", encoding="utf-8")

            row = review.assess_candidate(
                repo_root=root,
                spec_id="SPEC_stub",
                opportunity={"title": "Stub Product", "questions": {"who_pays": "buyer unclear"}},
                result_path=result,
            )

            self.assertTrue(row["low_quality"])
            self.assertIn(row["recommendation"], {"kill", "develop"})
            self.assertIn("flag", row["quality_take"])

    def test_portfolio_digest_names_reserved_boundary_and_recommendations(self) -> None:
        candidate = {
            "schema": "fpai_product_portfolio_review_v1",
            "count": 1,
            "low_quality_count": 1,
            "reserved_boundary": "James curates value. LAUNCH remains reserved.",
            "candidates": [
                {
                    "title": "Weak Product",
                    "quality_score": 35,
                    "quality_take": "weak proof",
                    "value_score": 70,
                    "value_take": "plausible",
                    "who_would_pay": "operators",
                    "recommendation": "develop",
                    "quality_flags": ["tests not proven"],
                }
            ],
        }

        text = review.render_review(candidate)

        self.assertIn("PORTFOLIO REVIEW", text)
        self.assertIn("QUALITY 35/100", text)
        self.assertIn("VALUE 70/100", text)
        self.assertIn("Rec: DEVELOP", text)
        self.assertIn("LAUNCH remains reserved", text)

    def test_cli_fail_on_low_quality_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "core/BUILD/results/SPEC_stub.result.md"
            result.parent.mkdir(parents=True)
            result.write_text("Summary: scaffold.\nTests: not run.\n", encoding="utf-8")

            out = StringIO()
            with redirect_stdout(out):
                code = review.main(
                    [
                        "--repo-root",
                        str(root),
                        "--spec-id",
                        "SPEC_stub",
                        "--result",
                        str(result),
                        "--json",
                        "--fail-on-low-quality",
                    ]
                )

            self.assertEqual(code, 3)
            self.assertTrue(json.loads(out.getvalue())["low_quality"])

    def test_failed_pytest_gate_report_forces_low_quality_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "core/BUILD/results/SPEC_bad.result.md"
            test_report = root / "core/BUILD/reports/SPEC_bad.test_gate.json"
            result.parent.mkdir(parents=True)
            test_report.parent.mkdir(parents=True)
            result.write_text(
                "Summary: Built endpoint.\nTests: pytest passed; py_compile; smoke passed.\n",
                encoding="utf-8",
            )
            test_report.write_text(
                json.dumps(
                    {
                        "schema": "fpai_build_loop_pytest_gate_v1",
                        "status": "failed",
                        "counts": {"passed": 2, "failed": 1, "errors": 0, "skipped": 0},
                    }
                ),
                encoding="utf-8",
            )

            row = review.assess_candidate(repo_root=root, spec_id="SPEC_bad", result_path=result)

            self.assertTrue(row["low_quality"])
            self.assertEqual(row["test_status"], "failed")
            self.assertIn("pytest gate failed", "; ".join(row["quality_flags"]))


if __name__ == "__main__":
    unittest.main()
