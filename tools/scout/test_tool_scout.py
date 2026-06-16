from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.scout import tool_scout


class ToolScoutTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-tool-scout-"))

    def fixture(self, root: Path, *, cost: float = 0.25, proposed_use: str = "Write a review-only adoption spec") -> Path:
        payload = {
            "cost_usd": cost,
            "candidates": [
                {
                    "name": "Fast Agent Runtime",
                    "url": "https://github.com/example/fast-agent",
                    "source_kind": "github",
                    "summary": "A fast runtime for local agent workflows.",
                    "proposed_use": proposed_use,
                    "replaces": "slow local orchestration",
                    "leverage": 9,
                    "maturity": 8,
                    "integration_cost": 3,
                    "risk": 2,
                    "released_at": "2026-06-01",
                    "evidence": ["release notes mention stable plugin API"],
                    "tags": ["agents", "runtime", "build"],
                },
                {
                    "name": "Risky Deploy Tool",
                    "url": "https://example.com/risky",
                    "source_kind": "product-release",
                    "summary": "High-risk deployment automation.",
                    "proposed_use": "Review as a future candidate",
                    "replaces": "",
                    "leverage": 7,
                    "maturity": 5,
                    "integration_cost": 8,
                    "risk": 8,
                    "tags": ["deploy"],
                },
            ],
        }
        path = root / "fixture.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_fixture_candidates_rank_and_write_artifacts(self) -> None:
        root = self.root()

        summary = tool_scout.run(
            focus="agent build runtime",
            fixture_path=self.fixture(root),
            report_path=root / "report.md",
            proposals_path=root / "proposals.jsonl",
            ops_ledger=root / "ops.jsonl",
        )

        self.assertEqual(summary["top"], "Fast Agent Runtime")
        self.assertEqual(summary["candidates"], 2)
        self.assertEqual(summary["proposals"], 1)
        report = (root / "report.md").read_text(encoding="utf-8")
        self.assertIn("Tool Scout Report", report)
        rows = [json.loads(line) for line in (root / "proposals.jsonl").read_text().splitlines()]
        self.assertEqual(rows[0]["source"], "tool_scout")
        self.assertEqual(rows[0]["verdict"], "adopt-spec")
        ledger = json.loads((root / "ops.jsonl").read_text().splitlines()[-1])
        self.assertEqual(ledger["loop"], "tool_scout")

    def test_cost_cap_blocks_provider_payload(self) -> None:
        root = self.root()

        with self.assertRaises(tool_scout.ToolScoutError):
            tool_scout.run(
                focus="agents",
                fixture_path=self.fixture(root, cost=2.0),
                report_path=root / "report.md",
                proposals_path=root / "proposals.jsonl",
                no_ledger=True,
            )

        self.assertFalse((root / "report.md").exists())

    def test_forbidden_action_in_proposed_use_fails_closed(self) -> None:
        root = self.root()

        with self.assertRaises(tool_scout.ToolScoutError):
            tool_scout.run(
                focus="agents",
                fixture_path=self.fixture(root, proposed_use="Install this in production"),
                report_path=root / "report.md",
                proposals_path=root / "proposals.jsonl",
                no_ledger=True,
            )

    def test_default_seed_scan_needs_no_provider(self) -> None:
        root = self.root()

        summary = tool_scout.run(
            focus="model router budget",
            report_path=root / "report.md",
            proposals_path=root / "proposals.jsonl",
            no_ledger=True,
        )

        self.assertGreaterEqual(summary["candidates"], 3)
        self.assertTrue((root / "report.md").exists())

    def test_live_collector_reads_github_search_and_release_payloads(self) -> None:
        class Response:
            def __init__(self, payload: dict[str, Any]):
                self.payload = payload

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *_exc: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(self.payload).encode("utf-8")

        def opener(request: Any, timeout: int) -> Response:
            url = request.full_url
            self.assertEqual(timeout, tool_scout.LIVE_TIMEOUT)
            if "/search/repositories" in url:
                return Response(
                    {
                        "items": [
                            {
                                "full_name": "example/new-agent-runtime",
                                "html_url": "https://github.com/example/new-agent-runtime",
                                "description": "New agent runtime",
                                "stargazers_count": 1200,
                                "pushed_at": "2026-06-10T00:00:00Z",
                            }
                        ]
                    }
                )
            return Response(
                {
                    "html_url": "https://github.com/example/release/releases/tag/v1",
                    "name": "Release v1",
                    "tag_name": "v1",
                    "published_at": "2026-06-11T00:00:00Z",
                }
            )

        payload = tool_scout.collect_live_payload(opener=opener)

        self.assertEqual(payload["provider_mode"], "live-github")
        candidates = tool_scout.validate_payload(payload)
        self.assertGreaterEqual(len(candidates), 2)
        self.assertTrue(any(candidate.source_kind == "github-search" for candidate in candidates))
        self.assertTrue(any(candidate.source_kind == "github-release" for candidate in candidates))


if __name__ == "__main__":
    unittest.main()
