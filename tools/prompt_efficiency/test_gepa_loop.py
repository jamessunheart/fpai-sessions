from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from tools.prompt_efficiency import gepa_loop


NOW = dt.datetime(2026, 6, 18, 22, 15, tzinfo=dt.timezone.utc)


class PromptEfficiencyLoopTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-d106-prompt-efficiency-"))

    def case_file(self, root: Path) -> Path:
        path = root / "cases.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "prompt-efficiency-cases.v1",
                    "cases": [
                        {
                            "id": "forge-trigger",
                            "prompt_id": "benchmark_improvement_spec",
                            "inputs": {
                                "score_row": {
                                    "agent": "forge",
                                    "trigger_metric": "first_pass_approve_rate",
                                    "primary_metric": 0.54,
                                    "trigger_reason": "below threshold",
                                    "metrics": {"first_pass_approve_rate": 0.54},
                                },
                                "resource_inventory": "- git: /usr/bin/git\n- fastapi==0.109.0\n",
                                "blueprint_text": "Forge should produce specs with proof and rollback.",
                                "recent_context": "Forge missed rollback evidence.",
                            },
                            "required_terms": [
                                "repo-build improvement spec",
                                "Return markdown only",
                                "production deploys",
                                "outreach sends",
                                "secrets",
                                "money movement",
                                "irreversible actions",
                                "Metrics JSON",
                                "Available resources on server 162",
                                "Do not request secret values",
                                "Forge missed rollback evidence",
                                "git: /usr/bin/git",
                            ],
                            "forbidden_terms": ["send the outreach now"],
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def test_compressed_guarded_wins_and_is_adopted(self) -> None:
        root = self.root()
        payload = gepa_loop.run(
            cases_path=self.case_file(root),
            adoptions_path=root / "adoptions.json",
            report_json=root / "report.json",
            report_md=root / "report.md",
            state_md=root / "state.md",
            now=NOW,
        )
        evaluation = payload["evaluations"][0]
        self.assertTrue(evaluation["adopted"])
        self.assertEqual(evaluation["winner"]["variant_id"], "compressed_guarded")
        self.assertGreaterEqual(evaluation["winner"]["quality"], evaluation["baseline"]["quality"])
        self.assertLess(evaluation["winner"]["avg_tokens"], evaluation["baseline"]["avg_tokens"])
        adoptions = json.loads((root / "adoptions.json").read_text(encoding="utf-8"))
        self.assertEqual(adoptions["adoptions"]["benchmark_improvement_spec"]["variant_id"], "compressed_guarded")

    def test_render_prompt_uses_adopted_variant_and_keeps_safety(self) -> None:
        root = self.root()
        (root / "adoptions.json").write_text(
            json.dumps(
                {
                    "schema": "prompt-efficiency-adoptions.v1",
                    "adoptions": {"benchmark_improvement_spec": {"variant_id": "compressed_guarded"}},
                }
            ),
            encoding="utf-8",
        )
        prompt = gepa_loop.render_prompt(
            "benchmark_improvement_spec",
            {
                "score_row": {
                    "agent": "forge",
                    "trigger_metric": "first_pass_approve_rate",
                    "primary_metric": 0.54,
                    "metrics": {},
                },
                "resource_inventory": "- git: /usr/bin/git\n",
                "recent_context": "Forge missed rollback evidence.",
            },
            adoptions_path=root / "adoptions.json",
        )
        self.assertIn("Safety: no production deploys", prompt)
        self.assertIn("Available resources on server 162", prompt)
        self.assertIn("Do not request secret values", prompt)
        self.assertIn("Forge missed rollback evidence", prompt)

    def test_sparse_variant_fails_quality_gate(self) -> None:
        root = self.root()
        cases = gepa_loop.load_cases(self.case_file(root))
        baseline_tokens = {"forge-trigger": gepa_loop.token_count(gepa_loop.render_benchmark_improvement_baseline(cases[0]["inputs"]))}
        sparse = gepa_loop.variant_for("benchmark_improvement_spec", "compressed_sparse")
        result = gepa_loop.evaluate_variant(sparse, cases, baseline_tokens)
        self.assertLess(result["quality"], 1.0)
        self.assertTrue(result["cases"][0]["required_misses"])


if __name__ == "__main__":
    unittest.main()

