from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

from tools.agent_benchmark_intelligence import engine


class AgentBenchmarkIntelligenceTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-d057-agent-benchmark-"))

    def make_registry(self, root: Path) -> tuple[Path, Path, Path]:
        registry = root / "core" / "BUILD" / "REGISTRY.json"
        results = root / "core" / "BUILD" / "results"
        reviews = root / "core" / "BUILD" / "reviews"
        results.mkdir(parents=True)
        reviews.mkdir(parents=True)
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": "SPEC_example",
                            "slug": "SPEC_example",
                            "status": "done",
                            "tests_passed": True,
                            "notes": "Independent review found blockers and findings fixed.",
                        },
                        {
                            "id": "SPEC_building",
                            "status": "building",
                            "tests_passed": False,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        (results / "SPEC_example.result.md").write_text(
            "# Result\n\n"
            "Tests: 4 tests OK\n\n"
            "Independent review: request_changes blockers fixed.\n\n"
            "Risks: sandbox only.\n\n"
            "Rollback: revert changed files.\n\n"
            "Intent solved: benchmark ledger exists.\n\n"
            "Downstream intent unlocked: route placement by measured evidence.\n",
            encoding="utf-8",
        )
        (reviews / "SPEC_example.review.md").write_text(
            "Finding: `tools/example.py:12` lacks a guard. Request changes.\n"
            "File evidence and line references make the critique actionable.\n",
            encoding="utf-8",
        )
        return registry, results, reviews

    def test_loads_fixture_and_infers_dimensions(self) -> None:
        root = self.root()
        fixture = root / "findings.json"
        fixture.write_text(
            json.dumps(
                {
                    "cost_usd": 0.0,
                    "findings": [
                        {
                            "source": "Fresh SWE-bench leaderboard",
                            "url": "https://example.test/swe",
                            "summary": "Code repository eval with unit test repair and reasoning.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        findings = engine.load_external_findings(fixture)

        self.assertEqual(len(findings), 1)
        self.assertGreater(findings[0].dimensions["code_quality"], 0)
        self.assertGreater(findings[0].dimensions["reasoning"], 0)

    def test_live_public_sources_use_fixed_urls(self) -> None:
        requested: list[str] = []

        class Response:
            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self, _limit: int = -1) -> bytes:
                return (
                    b"<html><title>SWE-bench</title> coding repository unit test "
                    b"reasoning benchmark leaderboard eval framework</html>"
                )

        def opener(request: object, timeout: int) -> Response:
            requested.append(request.full_url)  # type: ignore[attr-defined]
            self.assertEqual(timeout, engine.LIVE_TIMEOUT_SECONDS)
            return Response()

        findings = engine.load_external_findings(live_public_sources=True, opener=opener)

        self.assertEqual(len(findings), len(engine.PUBLIC_BENCHMARK_SOURCES))
        self.assertEqual(requested, [source["url"] for source in engine.PUBLIC_BENCHMARK_SOURCES])
        self.assertTrue(all(finding.source.startswith("live:") for finding in findings))

    def test_live_public_source_failures_fall_back_to_seed_evidence(self) -> None:
        def opener(_request: object, timeout: int) -> BytesIO:
            self.assertEqual(timeout, engine.LIVE_TIMEOUT_SECONDS)
            raise URLError("network unavailable")

        findings = engine.load_external_findings(live_public_sources=True, opener=opener)

        self.assertEqual(len(findings), len(engine.SEED_FINDINGS))
        self.assertTrue(any("live fetch failed" in " ".join(finding.evidence) for finding in findings))

    def test_partial_live_public_failures_are_reported(self) -> None:
        calls = 0

        class Response:
            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self, _limit: int = -1) -> bytes:
                return b"<html>coding reasoning benchmark eval framework with review evidence</html>"

        def opener(_request: object, timeout: int) -> Response:
            nonlocal calls
            self.assertEqual(timeout, engine.LIVE_TIMEOUT_SECONDS)
            calls += 1
            if calls == 2:
                raise URLError("one source failed")
            return Response()

        findings = engine.load_external_findings(live_public_sources=True, opener=opener)

        self.assertTrue(any(finding.source == "live:scan-warnings" for finding in findings))
        warning = next(finding for finding in findings if finding.source == "live:scan-warnings")
        self.assertIn("one source failed", " ".join(warning.evidence))

    def test_collects_internal_evidence_from_builds_and_reviews(self) -> None:
        root = self.root()
        registry, results, reviews = self.make_registry(root)

        evidence = engine.collect_internal_evidence(registry, results, reviews)

        self.assertEqual({row.agent_id for row in evidence}, {"codex-builder", "independent-reviewer"})
        builder = next(row for row in evidence if row.agent_id == "codex-builder")
        self.assertGreaterEqual(builder.metrics["code_quality"], 0.8)
        self.assertGreater(builder.metrics["learning_speed"], 0.5)

    def test_report_recommends_advisory_placements(self) -> None:
        root = self.root()
        registry, results, reviews = self.make_registry(root)
        findings = engine.load_external_findings()
        evidence = engine.collect_internal_evidence(registry, results, reviews)

        report = engine.build_report(external_findings=findings, internal_evidence=evidence, now="2026-06-16T00:00:00Z")

        self.assertEqual(report["schema"], engine.SCHEMA)
        self.assertEqual(report["ledger"]["schema"], engine.LEDGER_SCHEMA)
        self.assertTrue(report["mirror"]["agents"])
        self.assertTrue(all(agent["placement"]["authority"] == "advisory-only" for agent in report["mirror"]["agents"]))
        self.assertAlmostEqual(sum(report["lantern"]["dimension_weights"].values()), 1.0, places=3)

    def test_appends_one_ledger_row_per_agent(self) -> None:
        root = self.root()
        registry, results, reviews = self.make_registry(root)
        report = engine.build_report(
            external_findings=engine.load_external_findings(),
            internal_evidence=engine.collect_internal_evidence(registry, results, reviews),
            now="2026-06-16T00:00:00Z",
        )
        ledger = root / "ledger.jsonl"

        engine.append_ledger(engine.ledger_rows(report), ledger)
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(rows), len(report["mirror"]["agents"]))
        self.assertTrue(all(row["schema"] == engine.LEDGER_SCHEMA for row in rows))
        self.assertTrue(all(row["placement"]["gate"] for row in rows))

    def test_provider_cost_cap_fails_closed(self) -> None:
        root = self.root()
        fixture = root / "expensive.json"
        fixture.write_text(json.dumps({"cost_usd": 10.0, "findings": []}), encoding="utf-8")

        with self.assertRaises(ValueError):
            engine.load_external_findings(fixture)


if __name__ == "__main__":
    unittest.main()
