from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.hot_memory import run_all, synthesize
from tools.hot_memory.scanners import ops_scanner


class HotMemoryTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-hot-memory-"))
        (root / "core" / "BUILD" / "specs").mkdir(parents=True)
        (root / "core" / "BUILD" / "results").mkdir(parents=True)
        (root / "core" / "STATE" / "identity").mkdir(parents=True)
        (root / "docs" / "codex").mkdir(parents=True)
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": "SPEC_d112_hot-memory-architecture-5-domain",
                            "slug": "SPEC_d112_hot-memory-architecture-5-domain",
                            "branch": "build/SPEC_d112_hot-memory-architecture-5-domain",
                            "status": "building",
                        },
                        {"id": "SPEC_d111", "slug": "SPEC_d111", "branch": "build/SPEC_d111", "status": "done"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (root / "core" / "BUILD" / "specs" / "SPEC_d112_hot-memory-architecture-5-domain.md").write_text(
            "# d112\n",
            encoding="utf-8",
        )
        (root / "core" / "STATE" / "NOW.md").write_text(
            "**Decision filter:** does this grow the self-sustaining network or reduce external extraction dependency?\n"
            "### Priority: Self-sustaining network with dual sovereignty\n"
            "Narrator must be 100% truthful about WHAT IS.\n",
            encoding="utf-8",
        )
        (root / "core" / "STATE" / "NORTH_STAR.md").write_text("North Star: technical sovereignty and economic sovereignty.\n", encoding="utf-8")
        (root / "docs" / "codex" / "HANDOFF.md").write_text(
            "- **Intent solved:** hot memory one-doc context\n- **Downstream intent unlocked:** bot reliability probe\n",
            encoding="utf-8",
        )
        return root

    def test_run_all_writes_five_scanner_outputs(self) -> None:
        repo = self.make_repo()
        with tempfile.TemporaryDirectory() as tmp:
            hot_dir = Path(tmp)
            result = run_all.run_all(repo_root=repo, hot_dir=hot_dir, ops_ledger=repo / "ops.jsonl")
            files = sorted(path.name for path in hot_dir.glob("scanner_*.json"))

        self.assertTrue(result["ok"])
        self.assertEqual(
            files,
            [
                "scanner_decision.json",
                "scanner_identity.json",
                "scanner_ops.json",
                "scanner_signal.json",
                "scanner_spec.json",
            ],
        )

    def test_synthesize_writes_bounded_cited_hot_state_and_mirror(self) -> None:
        repo = self.make_repo()
        with tempfile.TemporaryDirectory() as tmp:
            hot_dir = Path(tmp) / "hot"
            output = Path(tmp) / "HOT_STATE.md"
            mirror = Path(tmp) / "repo" / "core" / "STATE" / "HOT_STATE.md"
            run_all.run_all(repo_root=repo, hot_dir=hot_dir, ops_ledger=repo / "ops.jsonl")
            rendered = synthesize.synthesize(hot_dir=hot_dir, output=output, mirror=mirror, max_chars=1600)
            output_text = output.read_text(encoding="utf-8")
            mirror_text = mirror.read_text(encoding="utf-8")

        self.assertLessEqual(len(rendered), 1600)
        self.assertIn("HOT_STATE", rendered)
        self.assertIn("Top pending build specs", rendered)
        self.assertIn("SPEC_d112_hot-memory-architecture-5-domain", rendered)
        self.assertIn("[source:", rendered)
        self.assertEqual(output_text, mirror_text)

    def test_synthesis_filters_secret_shaped_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hot_dir = Path(tmp) / "hot"
            hot_dir.mkdir()
            (hot_dir / "scanner_identity.json").write_text(
                json.dumps(
                    {
                        "facts": [
                            {
                                "text": "API token is abc123",
                                "source": "fixture",
                                "date": "2026-06-18",
                                "weight": 10,
                                "category": "directive",
                            },
                            {
                                "text": "System email is sunheartai@fullpotential.ai",
                                "source": "fixture",
                                "date": "2026-06-18",
                                "weight": 8,
                                "category": "general",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            rendered = synthesize.synthesize(hot_dir=hot_dir, output=Path(tmp) / "HOT_STATE.md", mirror=None)

        self.assertNotIn("abc123", rendered)
        self.assertIn("sunheartai@fullpotential.ai", rendered)

    def test_ops_scanner_surfaces_activation_audit_inert_builds(self) -> None:
        repo = self.make_repo()
        (repo / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": "SPEC_d099_unused",
                            "slug": "SPEC_d099_unused",
                            "branch": "build/SPEC_d099_unused",
                            "status": "merged",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        facts = ops_scanner.collect(repo_root=repo, ops_ledger=repo / "ops.jsonl")

        self.assertTrue(any("Activation audit: 1 unexplained INERT" in item.text for item in facts))


if __name__ == "__main__":
    unittest.main()
