#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("extract_intent_protocols.py")
SPEC = importlib.util.spec_from_file_location("extract_intent_protocols", SCRIPT_PATH)
extractor = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["extract_intent_protocols"] = extractor
SPEC.loader.exec_module(extractor)


class IntentProtocolExtractorTests(unittest.TestCase):
    def test_writes_protocol_files_with_frontmatter_and_skips_existing_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protocols = root / "memory" / "protocols"
            episodic = root / "memory" / "episodic"
            protocols.mkdir(parents=True)
            episodic.mkdir(parents=True)
            (protocols / "intent-should-update-protocols.md").write_text("existing\n", encoding="utf-8")
            (episodic / "session.md").write_text(
                "James: concentrate harder not build more\n",
                encoding="utf-8",
            )

            def runner(prompt: str) -> str:
                self.assertIn("tg_messages", prompt)
                self.assertIn("episodic_files", prompt)
                return json.dumps(
                    [
                        {
                            "slug": "concentrate-harder-not-build-more",
                            "rule": "When James asks for concentration, concentrate harder instead of building more.",
                            "source_date": "2026-06-16T01:00:00Z",
                        },
                        {
                            "slug": "intent-should-update-protocols",
                            "rule": "Intent clarifications should update durable protocols.",
                            "source_date": "2026-06-16",
                        },
                    ]
                )

            result = extractor.extract_protocols(
                memory_repo=root,
                protocols_dir=protocols,
                episodic_dir=episodic,
                read_telegram=False,
                claude_runner=runner,
                ops_ledger=root / "ops.jsonl",
                now=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
            )

            self.assertEqual(result.candidates, 2)
            self.assertEqual(result.written, 1)
            self.assertEqual(result.skipped, 1)
            written = protocols / "concentrate-harder-not-build-more.md"
            text = written.read_text(encoding="utf-8")
            self.assertIn("type: protocol", text)
            self.assertIn("source: intent-extractor", text)
            self.assertIn("date: 2026-06-16", text)
            self.assertIn("concentrate harder", text)

    def test_dry_run_does_not_write_or_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protocols = root / "memory" / "protocols"
            result = extractor.extract_protocols(
                memory_repo=root,
                protocols_dir=protocols,
                episodic_dir=root / "memory" / "episodic",
                read_telegram=False,
                claude_runner=lambda _prompt: json.dumps(
                    [
                        {
                            "slug": "case-study-first-then-template",
                            "rule": "Do the case study first, then make the template.",
                            "source_date": "2026-06-16",
                        }
                    ]
                ),
                ops_ledger=root / "ops.jsonl",
                dry_run=True,
                now=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
            )
            self.assertTrue(result.dry_run)
            self.assertEqual(result.written, 1)
            self.assertFalse((protocols / "case-study-first-then-template.md").exists())
            self.assertFalse((root / "ops.jsonl").exists())

    def test_proof_count_accepts_required_first_run_clarifications(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protocols = Path(tmp) / "memory" / "protocols"
            protocols.mkdir(parents=True)
            for phrase in extractor.PROOF_PHRASES:
                (protocols / f"{extractor.slugify(phrase)}.md").write_text(
                    f"---\ntype: protocol\nsource: intent-extractor\ndate: 2026-06-16\n---\n\n{phrase}\n",
                    encoding="utf-8",
                )
            self.assertEqual(extractor.proof_count(protocols), 3)

    def test_validate_protocols_normalizes_slug_and_dates(self) -> None:
        protocols = extractor.validate_protocols(
            [
                {"slug": " Intent should update protocols! ", "rule": "Intent should update protocols.", "source_date": "bad"},
                {"slug": "", "rule": "Case study first then template.", "source_date": "2026-06-16T03:00:00Z"},
                {"slug": "tiny", "rule": "no", "source_date": "2026-06-16"},
            ],
            fallback_date=datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual([p.slug for p in protocols], ["intent-should-update-protocols", "case-study-first-then-template"])
        self.assertEqual(protocols[0].source_date, "2026-06-17")
        self.assertEqual(protocols[1].source_date, "2026-06-16")


if __name__ == "__main__":
    unittest.main()
