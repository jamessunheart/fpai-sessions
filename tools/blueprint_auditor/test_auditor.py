from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.blueprint_auditor import auditor


class BlueprintAuditorTest(unittest.TestCase):
    def temp_root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-blueprint-auditor-"))

    def write_blueprint(self, root: Path, name: str, body: str) -> Path:
        bp = root / "blueprints"
        bp.mkdir(parents=True, exist_ok=True)
        path = bp / f"{name}.md"
        path.write_text(body, encoding="utf-8")
        return path

    def test_detects_missing_sections_and_vague_quality_standard(self) -> None:
        root = self.temp_root()
        path = self.write_blueprint(
            root,
            "forge",
            """# Forge Blueprint
## Identity
Owner: tools/build_loop

## Quality standard
Excellent and clear.
""",
        )

        findings = auditor.audit_blueprint(path)

        kinds = {finding.kind for finding in findings}
        self.assertIn("missing_section", kinds)
        self.assertIn("vague_quality_standard", kinds)

    def test_detects_undated_current_behavior_and_incomplete_integration(self) -> None:
        root = self.temp_root()
        path = self.write_blueprint(
            root,
            "health",
            """# Health Blueprint
## Identity
Owner: tools/test
## What it does
Runs smoke proof.
## How it works
Input: timer. Process: checks. Output: status. Side effects: ledger.
## Quality standard
Zero false green reports within 6 hours.
## Current behavior (verified)
Should run the smoke test and report health.
## Known gaps
- schema drift can still happen
## Integration map
- Depends on: tools/test
## Improvement history
initial seed
## Test coverage
Covered manually.
""",
        )

        findings = auditor.audit_blueprint(path)

        kinds = {finding.kind for finding in findings}
        self.assertIn("undated_current_behavior", kinds)
        self.assertIn("aspirational_current_behavior", kinds)
        self.assertIn("integration_map_incomplete", kinds)
        self.assertIn("history_undated", kinds)
        self.assertIn("test_coverage_vague", kinds)

    def test_run_writes_report_proposals_and_optional_ledger(self) -> None:
        root = self.temp_root()
        self.write_blueprint(
            root,
            "spark",
            """# Spark Blueprint
## Identity
Owner: tools/router
## What it does
Routes work.
## How it works
Input: signal. Process: classify. Output: route. Side effects: none.
## Quality standard
Every route has a pass/fail proof line.
## Current behavior (verified)
2026-06-16: route tests pass.
## Known gaps
none
## Integration map
- Depends on: tools/router
- Used by: build loop
- DB tables: none
- Kill switch: none
## Improvement history
2026-06-16 | d000 | seed | initial
## Test coverage
tools/router/test_route.py. Not tested: live DB.
""",
        )
        summary = auditor.run(
            blueprint_dir=root / "blueprints",
            report_path=root / "report.md",
            proposals_path=root / "proposals.jsonl",
            ops_ledger=root / "ops.jsonl",
        )

        self.assertGreater(summary["findings"], 0)
        self.assertTrue((root / "report.md").exists())
        rows = [json.loads(line) for line in (root / "proposals.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), summary["proposals"])
        self.assertEqual(rows[0]["source"], "blueprint_weakness_auditor")
        ledger = json.loads((root / "ops.jsonl").read_text().splitlines()[-1])
        self.assertEqual(ledger["loop"], "blueprint_weakness_auditor")


if __name__ == "__main__":
    unittest.main()
