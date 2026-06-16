from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.docs import generate_architecture


REGISTRY = {
    "active_builds": [
        {"id": "SPEC_d038_content-bank", "status": "done", "branch": "build/SPEC_d038"},
        {"id": "SPEC_d010_self-evolution", "status": "done", "branch": "build/SPEC_d010"},
    ]
}

DECISIONS = [
    {"id": "48", "title": "Living Architecture Doc", "status": "building"},
    {"id": "49", "title": "Next planned surface", "status": "answered"},
]

SERVICES = [
    {"service": "sh-brain-tgbot", "host": "162", "runs": "loaded/active/running - Telegram owner chat"},
    {"service": "fpai-build-loop.timer", "host": "162", "runs": "loaded/active/waiting - build loop timer"},
    {"service": "fpai-council.timer", "host": "162", "runs": "loaded/active/waiting - council timer"},
    {"service": "fpai-morning-digest.timer", "host": "162", "runs": "loaded/active/waiting - visual digest"},
    {"service": "brain_index", "host": "162:25432", "runs": "Postgres schema tables: decisions"},
]


class ArchitectureGeneratorTests(unittest.TestCase):
    def test_all_9_sections_present(self) -> None:
        text = generate_architecture.render_architecture(
            registry=REGISTRY,
            decisions=DECISIONS,
            services=SERVICES,
            generated_at="2026-06-16T00:00:00Z",
        )

        for number, title in (
            (1, "What this system is"),
            (2, "The 9 functions"),
            (3, "Data flow diagram"),
            (4, "Build loop"),
            (5, "Infrastructure"),
            (6, "Decision queue snapshot"),
            (7, "Key files"),
            (8, "What to ask GPT / how to share"),
            (9, "Gap log"),
        ):
            self.assertIn(f"## {number}. {title}", text)

    def test_mermaid_block_present_and_parseable_shape(self) -> None:
        text = generate_architecture.render_architecture(
            registry=REGISTRY,
            decisions=DECISIONS,
            services=SERVICES,
            generated_at="2026-06-16T00:00:00Z",
        )

        match = re.search(r"```mermaid\n(.*?)\n```", text, re.S)
        self.assertIsNotNone(match)
        diagram = match.group(1)
        self.assertTrue(diagram.startswith("flowchart TD"))
        self.assertIn("B[Beacon\\nQR/ad/link] --> H[Hermes Gateway\\nchannel normalizer]", diagram)
        self.assertEqual(diagram.count("["), diagram.count("]"))

    def test_decision_queue_snapshot_populated_from_decision_rows(self) -> None:
        text = generate_architecture.render_architecture(
            registry=REGISTRY,
            decisions=DECISIONS,
            services=SERVICES,
            generated_at="2026-06-16T00:00:00Z",
        )

        self.assertIn("| d048 | Living Architecture Doc | building |", text)
        self.assertIn("| d049 | Next planned surface | answered |", text)

    def test_gap_log_lists_needs_build_decisions(self) -> None:
        text = generate_architecture.render_architecture(
            registry=REGISTRY,
            decisions=DECISIONS,
            services=SERVICES,
            generated_at="2026-06-16T00:00:00Z",
        )

        self.assertIn("building d048 - Living Architecture Doc", text)
        self.assertIn("planned d049 - Next planned surface", text)

    def test_generate_is_idempotent_after_normalizing_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "REGISTRY.json"
            output = root / "ARCHITECTURE.md"
            ledger = root / "ops.jsonl"
            registry.write_text(json.dumps(REGISTRY), encoding="utf-8")

            generate_architecture.generate(
                output=output,
                registry_path=registry,
                ops_ledger=ledger,
                decisions=DECISIONS,
                services=SERVICES,
                log=True,
            )
            first = output.read_text(encoding="utf-8")
            generate_architecture.generate(
                output=output,
                registry_path=registry,
                ops_ledger=ledger,
                decisions=DECISIONS,
                services=SERVICES,
                log=True,
            )
            second = output.read_text(encoding="utf-8")
            normalize = lambda text: re.sub(r"at .*?\. Do not", "at <ts>. Do not", text)
            self.assertEqual(normalize(first), normalize(second))
            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[-1]["event"], "architecture_generated")
            self.assertEqual(rows[-1]["sections"], 9)

    def test_disable_skips_auto_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"ARCHITECTURE_DISABLE": "1"}):
            output = Path(tmp) / "ARCHITECTURE.md"
            result = generate_architecture.generate(output=output, log=False)

        self.assertTrue(result["disabled"])
        self.assertFalse(output.exists())

    def test_merge_paths_call_generate_architecture_after_merge(self) -> None:
        root = generate_architecture.REPO_ROOT
        process_merge = (root / "tools" / "merge" / "process_merge_requests.sh").read_text(encoding="utf-8")
        orchestrator = (root / "tools" / "build_loop" / "build_orchestrator.sh").read_text(encoding="utf-8")

        for script in (process_merge, orchestrator):
            self.assertIn("tools/docs/generate_architecture.py", script)
            self.assertIn("docs(architecture): auto-regenerate after merge", script)


if __name__ == "__main__":
    unittest.main()
